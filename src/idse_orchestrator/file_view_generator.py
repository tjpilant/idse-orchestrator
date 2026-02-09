from __future__ import annotations

from pathlib import Path
from typing import Dict, Iterable, List, Optional
import json
import re
import warnings

from .artifact_database import ArtifactDatabase, hash_content
from .design_store import DesignStoreFilesystem


class FileViewGenerator:
    """Generate IDE-friendly markdown views from SQLite artifacts."""

    def __init__(
        self,
        db_path: Optional[Path] = None,
        idse_root: Optional[Path] = None,
        allow_create: bool = False,
    ):
        if idse_root is None:
            from .project_workspace import ProjectWorkspace

            manager = ProjectWorkspace()
            idse_root = manager.idse_root

        self.idse_root = Path(idse_root)
        self.projects_root = self.idse_root / "projects"
        self.db = ArtifactDatabase(db_path=db_path, idse_root=self.idse_root, allow_create=allow_create)

    def generate_session(
        self,
        project: str,
        session_id: str,
        stages: Optional[Iterable[str]] = None,
    ) -> List[Path]:
        stage_list = list(stages) if stages else list(DesignStoreFilesystem.STAGE_PATHS.keys())
        written: List[Path] = []
        session_path = self.projects_root / project / "sessions" / session_id

        for stage in stage_list:
            if stage not in DesignStoreFilesystem.STAGE_PATHS:
                continue
            try:
                record = self.db.load_artifact(project, session_id, stage)
            except FileNotFoundError:
                continue
            folder, filename = DesignStoreFilesystem.STAGE_PATHS[stage]
            artifact_path = session_path / folder / filename
            artifact_path.parent.mkdir(parents=True, exist_ok=True)
            artifact_path.write_text(record.content)
            written.append(artifact_path)

        return written

    def generate_project(
        self,
        project: str,
        sessions: Optional[Iterable[str]] = None,
        stages: Optional[Iterable[str]] = None,
    ) -> Dict[str, List[Path]]:
        session_ids = list(sessions) if sessions else self.db.list_sessions(project)
        results: Dict[str, List[Path]] = {}
        for session_id in session_ids:
            results[session_id] = self.generate_session(project, session_id, stages=stages)
        return results

    def generate_session_state(self, project: str, session_id: str) -> Path:
        state = self.db.load_session_state(project, session_id)
        project_path = self.projects_root / project
        state_path = project_path / "session_state.json"
        state_path.write_text(json.dumps(state, indent=2))
        return state_path

    def generate_agent_registry(self, project: str) -> Optional[Path]:
        registry = self.db.load_agent_registry(project)
        if not registry:
            return None
        project_path = self.projects_root / project
        registry_path = project_path / "agent_registry.json"
        registry_path.write_text(json.dumps(registry, indent=2))
        return registry_path

    def generate_blueprint_meta(self, project: str) -> Path:
        self.ensure_blueprint_scope(project)
        integrity_warning = self.verify_blueprint_integrity(project)
        if integrity_warning:
            warnings.warn(integrity_warning, stacklevel=2)
        sessions = self.db.list_session_metadata(project)
        sessions.sort(key=lambda s: (0 if s["session_id"] == "__blueprint__" else 1, s["created_at"]))
        blueprint_meta = self.projects_root / project / "sessions" / "__blueprint__" / "metadata" / "meta.md"
        existing_meta = blueprint_meta.read_text() if blueprint_meta.exists() else ""
        preserved_narrative = _extract_custom_narrative(existing_meta)
        active_statuses = {"draft", "in_progress", "review"}

        registry_lines = []
        matrix_rows = []
        for meta in sessions:
            is_active = meta["session_id"] == "__blueprint__" or meta.get("status") in active_statuses
            if meta["session_id"] == "__blueprint__" and is_active:
                registry_lines.append("- `__blueprint__` (THIS SESSION) - Project governance and roadmap")
            elif is_active:
                description = meta.get("description") or "Feature session"
                registry_lines.append(f"- `{meta['session_id']}` - {description}")
            progress = self._session_progress(project, meta["session_id"])
            matrix_rows.append(
                f"| {meta['session_id']} | {meta['session_type']} | {meta['status']} |"
                f" {meta.get('owner') or 'system'} | {meta['created_at'][:10]} | {progress}% |"
            )

        registry_section = "\n".join(registry_lines) if registry_lines else "(To be added as sessions are created)"
        matrix_section = "\n".join([
            "| Session ID | Type | Status | Owner | Created | Progress |",
            "|------------|------|--------|-------|---------|----------|",
        ] + matrix_rows)
        lineage_graph = self._build_lineage_graph(sessions)
        delivery_summary = self._build_delivery_summary(project, sessions)
        feedback_summary = self._build_feedback_summary(project, sessions)
        promotion_records = self._build_promotion_records(project)
        demotion_records = self._build_demotion_records(project)

        content = f"""# {project} - Blueprint Meta

## Session Registry

This document tracks all sessions spawned from this Blueprint.

### Active Sessions
{registry_section}

## Session Status Matrix

{matrix_section}

## Lineage Graph

```
{lineage_graph}
```

## Governance

Authoritative scope is defined in `blueprint.md`.
- `meta.md` is derived from runtime session state in SQLite.
- Use `blueprint.md` to define or change project intent, constraints, and invariants.
- Use `meta.md` to monitor delivery, feedback, and alignment across sessions.

## Feedback Loop

Feedback from Feature Sessions flows upward to inform Blueprint updates.

## Delivery Summary

{delivery_summary}

## Feedback & Lessons Learned

{feedback_summary}

## Blueprint Promotion Record

{promotion_records}

## Demotion Record

{demotion_records}

## Meta Narrative

<!-- BEGIN CUSTOM NARRATIVE -->
{preserved_narrative}
<!-- END CUSTOM NARRATIVE -->

---
*Last updated: {_now()}*
"""
        blueprint_meta.parent.mkdir(parents=True, exist_ok=True)
        blueprint_meta.write_text(content)
        return blueprint_meta

    def ensure_blueprint_scope(self, project: str) -> Path:
        blueprint_scope = (
            self.projects_root / project / "sessions" / "__blueprint__" / "metadata" / "blueprint.md"
        )
        if blueprint_scope.exists():
            return blueprint_scope
        blueprint_scope.parent.mkdir(parents=True, exist_ok=True)
        blueprint_scope.write_text(
            f"""# {project} - Blueprint

> Append-only via promotion gate.

## Purpose
- Define project intent and long-lived outcomes.

## System Boundaries
- Define what is in scope and out of scope for this project.

## Core Invariants
- Record non-negotiable constraints the implementation must preserve.

## High-Level Architecture
- Describe major components, interfaces, and data ownership boundaries.

## Stakeholders
- List owners, collaborators, and impacted users/systems.

## Constraints & Risks
- Capture operational, technical, and governance constraints with mitigation strategy.

## Promoted Converged Intent
- No converged intent promoted yet.
"""
        )
        return blueprint_scope

    def apply_allowed_promotions_to_blueprint(self, project: str, *, accept_mismatch: bool = False) -> Path:
        path = self.ensure_blueprint_scope(project)
        integrity_warning = self.verify_blueprint_integrity(project)
        if integrity_warning:
            warnings.warn(integrity_warning, stacklevel=2)
        mismatch_unresolved = integrity_warning is not None and not accept_mismatch
        content = path.read_text()
        marker = "## Promoted Converged Intent"
        if marker not in content:
            return path

        rows = self.db.list_blueprint_promotions(project, status="ALLOW")
        claims = [f"- [{row['classification']}] {row['claim_text']}" for row in rows]
        if not claims:
            return path

        rebuilt = _append_unique_bullets_to_section(
            content,
            marker,
            claims,
            placeholder="- No converged intent promoted yet.",
        )
        existing_claims = self.db.get_blueprint_claims(project)
        existing_claim_texts = {claim["claim_text"] for claim in existing_claims}
        for row in rows:
            if row["claim_text"] not in existing_claim_texts:
                self.db.save_blueprint_claim(
                    project,
                    claim_text=row["claim_text"],
                    classification=row["classification"],
                    promotion_record_id=row["id"],
                )
        active_claim_texts = {
            claim["claim_text"] for claim in self.db.get_blueprint_claims(project, status="active")
        }
        active_rows = [row for row in rows if row["claim_text"] in active_claim_texts]

        by_section: Dict[str, List[str]] = {}
        for row in active_rows:
            heading = _resolve_blueprint_section(row["claim_text"], row["classification"])
            by_section.setdefault(heading, []).append(f"- {row['claim_text']}")

        section_heads = [
            "## Purpose",
            "## System Boundaries",
            "## Core Invariants",
            "## High-Level Architecture",
            "## Stakeholders",
            "## Constraints & Risks",
        ]
        for heading in section_heads:
            rebuilt = _rebuild_section_bullets(rebuilt, heading, by_section.get(heading, []))
        path.write_text(rebuilt)
        if accept_mismatch and integrity_warning:
            stored = self.db.get_blueprint_hash(project)
            self.db.record_integrity_event(
                project,
                expected_hash=stored or "",
                actual_hash=hash_content(rebuilt),
                action="accept",
            )
        if not mismatch_unresolved:
            self.db.save_blueprint_hash(project, hash_content(rebuilt))
        return path

    def verify_blueprint_integrity(self, project: str) -> Optional[str]:
        path = self.ensure_blueprint_scope(project)
        if not path.exists():
            return None
        expected_hash = self.db.get_blueprint_hash(project)
        if not expected_hash:
            return None
        actual_hash = hash_content(path.read_text())
        if actual_hash == expected_hash:
            return None
        self.db.record_integrity_event(
            project,
            expected_hash=expected_hash,
            actual_hash=actual_hash,
            action="warn",
        )
        return (
            "Blueprint integrity mismatch detected: "
            f"expected {expected_hash[:12]}..., got {actual_hash[:12]}...."
        )

    def _build_promotion_records(self, project: str) -> str:
        rows = self.db.list_blueprint_promotions(project, status="ALLOW")
        if not rows:
            return "- No promoted claims recorded yet."
        all_claims = {claim["claim_text"]: claim for claim in self.db.get_blueprint_claims(project)}
        deduped: Dict[tuple[str, str], Dict] = {}
        for row in rows:
            key = (row["claim_text"], row["evidence_hash"])
            current = deduped.get(key)
            current_ts = (current or {}).get("promoted_at") or (current or {}).get("created_at") or ""
            row_ts = row.get("promoted_at") or row.get("created_at") or ""
            if current is None or row_ts > current_ts:
                deduped[key] = row
        ordered_rows = sorted(
            deduped.values(),
            key=lambda row: row.get("promoted_at") or row.get("created_at") or "",
            reverse=True,
        )
        lines: List[str] = []
        for row in ordered_rows:
            evidence = row.get("evidence") or {}
            sessions = evidence.get("source_sessions") or []
            stages = evidence.get("source_stages") or []
            feedback_artifacts = evidence.get("feedback_artifacts") or []
            feedback_ids = [item.get("idse_id", "unknown") for item in feedback_artifacts]
            lines.extend(
                [
                    f"- Date: {row.get('promoted_at') or row.get('created_at')}",
                    f"  Promoted Claim: {row['claim_text']}",
                    f"  Classification: {row['classification']}",
                    f"  Source Sessions: {', '.join(sessions) if sessions else 'none'}",
                    f"  Source Stages: {', '.join(stages) if stages else 'none'}",
                    f"  Feedback Artifacts: {', '.join(feedback_ids) if feedback_ids else 'none'}",
                    f"  Evidence Hash: {row['evidence_hash']}",
                    f"  Lifecycle: {all_claims.get(row['claim_text'], {}).get('status', 'unknown')}",
                ]
            )
        return "\n".join(lines)

    def _build_demotion_records(self, project: str) -> str:
        events = self.db.get_lifecycle_events(project)
        demotions = [event for event in events if event["new_status"] in {"superseded", "invalidated"}]
        if not demotions:
            return "- No demotion events recorded."
        lines: List[str] = []
        for event in demotions:
            lines.extend(
                [
                    f"- Date: {event['created_at']}",
                    f"  Claim ID: {event['claim_id']}",
                    f"  Transition: {event['old_status']} -> {event['new_status']}",
                    f"  Reason: {event['reason']}",
                    f"  Actor: {event['actor']}",
                ]
            )
            if event.get("superseding_claim_id"):
                lines.append(f"  Superseded by: claim {event['superseding_claim_id']}")
        return "\n".join(lines)

    def _build_lineage_graph(self, sessions: List[Dict]) -> str:
        by_parent: Dict[str, List[str]] = {}
        session_ids = {session["session_id"] for session in sessions}
        for session in sessions:
            session_id = session["session_id"]
            if session_id == "__blueprint__":
                continue
            parent = session.get("parent_session") or "__blueprint__"
            if parent not in session_ids:
                parent = "__blueprint__"
            by_parent.setdefault(parent, []).append(session_id)

        lines: List[str] = ["__blueprint__ (root)"]

        def walk(parent: str, prefix: str) -> None:
            children = sorted(by_parent.get(parent, []))
            for idx, child in enumerate(children):
                is_last = idx == len(children) - 1
                connector = "└── " if is_last else "├── "
                lines.append(f"{prefix}{connector}{child}")
                child_prefix = f"{prefix}{'    ' if is_last else '│   '}"
                walk(child, child_prefix)

        walk("__blueprint__", "")
        return "\n".join(lines)

    def _session_progress(self, project: str, session_id: str) -> int:
        try:
            state = self.db.load_session_state(project, session_id)
        except FileNotFoundError:
            return 0
        stages = state.get("stages") or {}
        if not stages:
            return 0
        completed = sum(1 for value in stages.values() if value == "completed")
        total = len(stages)
        if total == 0:
            return 0
        return int(round((completed / total) * 100))

    def _build_delivery_summary(self, project: str, sessions: List[Dict]) -> str:
        lines: List[str] = []
        for meta in sessions:
            session_id = meta["session_id"]
            if session_id == "__blueprint__":
                continue
            if not self._session_is_reportable(project, session_id):
                continue
            summary_items = self._extract_implementation_summary(project, session_id)
            if summary_items:
                lines.append(f"- `{session_id}`: {'; '.join(summary_items)}")
        if not lines:
            return "- No implementation summaries recorded yet."
        return "\n".join(lines)

    def _build_feedback_summary(self, project: str, sessions: List[Dict]) -> str:
        lines: List[str] = []
        for meta in sessions:
            session_id = meta["session_id"]
            if session_id == "__blueprint__":
                continue
            if not self._session_is_reportable(project, session_id):
                continue
            summary_items = self._extract_feedback_summary(project, session_id)
            if summary_items:
                lines.append(f"- `{session_id}`: {'; '.join(summary_items)}")
        if not lines:
            return "- No feedback summaries recorded yet."
        return "\n".join(lines)

    def _extract_implementation_summary(self, project: str, session_id: str) -> List[str]:
        try:
            content = self.db.load_artifact(project, session_id, "implementation").content
        except FileNotFoundError:
            return []

        if "[REQUIRES INPUT]" in content:
            return []

        bullets = _extract_summary_bullets(
            content,
            [
                "Summary",
                "Executive Summary",
                "Completion Record",
                "Workflow",
                "Fixes",
                "Validation",
            ],
        )
        if bullets:
            return [_truncate(item, 200) for item in bullets[:5]]

        # Fallback: first sentence-like line in the implementation artifact.
        for line in content.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if _is_placeholder_text(stripped):
                continue
            if len(stripped) >= 12:
                return [_truncate(stripped, 200)]
        return []

    def _extract_feedback_summary(self, project: str, session_id: str) -> List[str]:
        try:
            content = self.db.load_artifact(project, session_id, "feedback").content
        except FileNotFoundError:
            return []

        if "[REQUIRES INPUT]" in content:
            return []

        bullets = _extract_summary_bullets(
            content,
            [
                "Summary",
                "Lessons Learned",
                "Completion Notes",
                "Decision Log",
                "Validation",
                "Executive Summary",
            ],
        )
        if bullets:
            return [_truncate(item, 200) for item in bullets[:5]]

        for line in content.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if _is_placeholder_text(stripped):
                continue
            if len(stripped) >= 12:
                return [_truncate(stripped, 200)]
        return []

    def _session_is_reportable(self, project: str, session_id: str) -> bool:
        # Exclude sessions with no meaningful artifact content. This prevents
        # placeholders/empty sessions from polluting high-level rollups.
        found_meaningful = False
        for stage in DesignStoreFilesystem.STAGE_PATHS:
            try:
                content = self.db.load_artifact(project, session_id, stage).content
            except FileNotFoundError:
                continue
            if not content.strip():
                continue
            if "[REQUIRES INPUT]" in content:
                continue
            if _meaningful_text_length(content) < 40:
                continue
            found_meaningful = True
            break
        return found_meaningful


def _now() -> str:
    from datetime import datetime

    return datetime.now().isoformat()


def _extract_markdown_section_variants(content: str, section_names: List[str]) -> Optional[str]:
    normalized_targets = {_normalize_heading_name(name) for name in section_names}
    lines = content.splitlines()
    start = None
    for idx, line in enumerate(lines):
        heading_match = re.match(r"^\s*#{1,3}\s+(.+?)\s*$", line)
        if not heading_match:
            continue
        heading_name = _normalize_heading_name(heading_match.group(1))
        if heading_name in normalized_targets:
            start = idx + 1
            break
    if start is None:
        return None

    end = len(lines)
    for idx in range(start, len(lines)):
        if re.match(r"^\s*#{1,3}\s+.+$", lines[idx]):
            end = idx
            break
    return "\n".join(lines[start:end]).strip()


def _extract_bullets(section: str) -> List[str]:
    bullets: List[str] = []
    for line in section.splitlines():
        stripped = line.strip()
        if stripped.startswith("- "):
            bullets.append(stripped[2:].strip())
        elif stripped.startswith("* "):
            bullets.append(stripped[2:].strip())
    return [item for item in bullets if item and not _is_placeholder_text(item)]


def _extract_summary_bullets(content: str, section_names: List[str]) -> List[str]:
    # Prefer explicit summary-style sections first.
    collected: List[str] = []
    for section_name in section_names:
        section = _extract_markdown_section_variants(content, [section_name])
        if not section:
            continue
        for item in _extract_bullets(section):
            if item not in collected:
                collected.append(item)
    if collected:
        return collected

    # Fallback to any bullets in the document.
    all_bullets = _extract_bullets(content)
    deduped: List[str] = []
    for item in all_bullets:
        if item not in deduped:
            deduped.append(item)
    return deduped


def _extract_custom_narrative(content: str) -> str:
    begin = "<!-- BEGIN CUSTOM NARRATIVE -->"
    end = "<!-- END CUSTOM NARRATIVE -->"
    if begin in content and end in content:
        start = content.index(begin) + len(begin)
        finish = content.index(end, start)
        narrative = content[start:finish].strip("\n")
        if narrative.strip():
            return narrative
    return (
        "Use this section for high-detail meta context that should survive metadata regeneration.\n"
        "- Architecture rationale\n"
        "- Cross-session decisions\n"
        "- Risks and mitigation notes"
    )


def _append_unique_bullets_to_section(
    content: str,
    heading: str,
    bullets: List[str],
    *,
    placeholder: Optional[str] = None,
) -> str:
    if heading not in content:
        return content

    section_start = content.index(heading) + len(heading)
    tail = content[section_start:]
    next_heading_idx = tail.find("\n## ")
    if next_heading_idx == -1:
        section_body = tail.strip("\n")
        suffix = ""
    else:
        section_body = tail[:next_heading_idx].strip("\n")
        suffix = tail[next_heading_idx:]

    existing_lines = [line.strip() for line in section_body.splitlines() if line.strip()]
    merged = list(existing_lines)
    if placeholder:
        merged = [line for line in merged if line != placeholder]
    for bullet in bullets:
        if bullet not in merged:
            merged.append(bullet)
    if not merged and placeholder:
        merged = [placeholder]

    rebuilt = content[:section_start] + "\n" + "\n".join(merged)
    if suffix:
        rebuilt += suffix
    return rebuilt


def _rebuild_section_bullets(content: str, heading: str, bullets: List[str]) -> str:
    if heading not in content:
        return content
    section_start = content.index(heading) + len(heading)
    tail = content[section_start:]
    next_heading_idx = tail.find("\n## ")
    if next_heading_idx == -1:
        section_body = tail.strip("\n")
        suffix = ""
    else:
        section_body = tail[:next_heading_idx].strip("\n")
        suffix = tail[next_heading_idx:]

    preamble = []
    for line in section_body.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("- "):
            continue
        preamble.append(stripped)
    merged = preamble + bullets
    rebuilt = content[:section_start] + "\n" + "\n".join(merged)
    if suffix:
        rebuilt += suffix
    return rebuilt


def _resolve_blueprint_section(claim_text: str, classification: str) -> str:
    lowered = claim_text.lower()
    if any(token in lowered for token in ["documentation os", "purpose", "intent-driven systems engineering"]):
        return "## Purpose"
    if classification == "boundary" or any(token in lowered for token in ["in scope", "out of scope", "boundary"]):
        return "## System Boundaries"
    if classification == "ownership_rule" or any(token in lowered for token in ["owner", "ownership", "collaborator", "stakeholder"]):
        return "## Stakeholders"
    if any(token in lowered for token in ["architecture", "component", "interface", "data ownership"]):
        return "## High-Level Architecture"
    if classification == "invariant":
        return "## Core Invariants"
    return "## Constraints & Risks"


def _normalize_heading_name(name: str) -> str:
    return re.sub(r"\s+", " ", name.strip().lower())


def _truncate(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 3)].rstrip() + "..."


def _meaningful_text_length(content: str) -> int:
    text = re.sub(r"```[\s\S]*?```", "", content)
    text = re.sub(r"`[^`]*`", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return len(text)


def _is_placeholder_text(text: str) -> bool:
    lowered = text.strip().lower()
    if not lowered:
        return True
    if "requires input" in lowered:
        return True
    if lowered.startswith("todo"):
        return True
    if "todo" in lowered:
        return True
    if "summarize feedback received" in lowered:
        return True
    return False
