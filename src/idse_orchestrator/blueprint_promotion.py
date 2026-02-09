from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from difflib import SequenceMatcher
from hashlib import sha256
import json
import re
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

from .artifact_database import ArtifactDatabase


CONSTITUTIONAL_CLASSES = {
    "invariant",
    "boundary",
    "ownership_rule",
    "non_negotiable_constraint",
}


@dataclass
class PromotionDecision:
    status: str
    failed_tests: List[str]
    evidence: Dict[str, Any]
    evidence_hash: str


@dataclass
class PromotionCandidate:
    claim_text: str
    source_refs: List[Tuple[str, str]]
    support_count: int
    session_count: int
    stage_count: int
    suggested_classification: str


class BlueprintPromotionGate:
    def __init__(self, db: ArtifactDatabase):
        self.db = db

    def evaluate_promotion(
        self,
        project: str,
        *,
        claim_text: str,
        classification: str,
        source_refs: Iterable[Tuple[str, str]],
        min_convergence_days: int = 7,
    ) -> PromotionDecision:
        failed: List[str] = []
        source_rows = self._load_sources(project, list(source_refs))
        distinct_sessions = sorted({row["session_id"] for row in source_rows})
        distinct_stages = sorted({row["stage"] for row in source_rows})

        if len(distinct_sessions) < 2:
            failed.append("INSUFFICIENT_SESSION_DIVERSITY")
        if len(distinct_stages) < 2:
            failed.append("INSUFFICIENT_STAGE_DIVERSITY")

        snippets = [row["snippet"] for row in source_rows if row["snippet"]]
        fingerprints = [row["semantic_fingerprint"] for row in source_rows if row["semantic_fingerprint"]]
        max_sim = self._max_pairwise_similarity(snippets, fingerprints)
        if max_sim > 0.98:
            failed.append("DUPLICATE_STATEMENT")

        if classification not in CONSTITUTIONAL_CLASSES:
            failed.append("NOT_CONSTITUTIONAL")

        feedback_rows = self._load_feedback(project, distinct_sessions)
        feedback_signals = self.db.list_feedback_signals(project, distinct_sessions)
        if not feedback_rows and not feedback_signals:
            failed.append("NO_FEEDBACK_EVIDENCE")
        elif any(
            _has_contradiction(item["content"]) for item in feedback_rows
        ) or any(bool(item.get("contradiction_flag")) for item in feedback_signals):
            failed.append("CONTRADICTED_BY_FEEDBACK")

        if source_rows:
            min_ts = min(_parse_dt(row["created_at"]) for row in source_rows)
            max_ts = max(_parse_dt(row["created_at"]) for row in source_rows)
            if (max_ts - min_ts).days < min_convergence_days:
                failed.append("INSUFFICIENT_TEMPORAL_STABILITY")

        evidence = {
            "claim_text": claim_text,
            "classification": classification,
            "source_sessions": distinct_sessions,
            "source_stages": distinct_stages,
            "source_artifacts": [
                {
                    "artifact_id": row["artifact_id"],
                    "session_id": row["session_id"],
                    "stage": row["stage"],
                    "idse_id": row["idse_id"],
                    "content_hash": row["content_hash"],
                    "semantic_fingerprint": row["semantic_fingerprint"],
                    "created_at": row["created_at"],
                    "snippet": row["snippet"],
                }
                for row in source_rows
            ],
            "feedback_artifacts": [
                {
                    "artifact_id": row["artifact_id"],
                    "session_id": row["session_id"],
                    "idse_id": row["idse_id"],
                    "created_at": row["created_at"],
                    "contradiction_flag": _has_contradiction(row["content"]),
                }
                for row in feedback_rows
            ],
            "max_pairwise_similarity": max_sim,
            "feedback_signal_count": len(feedback_signals),
            "min_convergence_days": min_convergence_days,
        }
        evidence_hash = sha256(
            json.dumps(evidence, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        status = "ALLOW" if not failed else "DENY"
        return PromotionDecision(
            status=status,
            failed_tests=failed,
            evidence=evidence,
            evidence_hash=evidence_hash,
        )

    def evaluate_and_record(
        self,
        project: str,
        *,
        claim_text: str,
        classification: str,
        source_refs: Iterable[Tuple[str, str]],
        min_convergence_days: int = 7,
        dry_run: bool = False,
    ) -> PromotionDecision:
        decision = self.evaluate_promotion(
            project,
            claim_text=claim_text,
            classification=classification,
            source_refs=source_refs,
            min_convergence_days=min_convergence_days,
        )
        if dry_run:
            return decision

        source_artifact_ids = [
            row["artifact_id"] for row in decision.evidence.get("source_artifacts", [])
        ]
        promoted_at = datetime.now().isoformat() if decision.status == "ALLOW" else None
        self.db.save_blueprint_promotion(
            project,
            claim_text=claim_text,
            classification=classification,
            status=decision.status,
            evidence_hash=decision.evidence_hash,
            failed_tests=decision.failed_tests,
            evidence=decision.evidence,
            source_artifact_ids=source_artifact_ids,
            promoted_at=promoted_at,
        )
        return decision

    def demote_claim(
        self,
        project: str,
        *,
        claim_id: int,
        reason: str,
        new_status: str = "invalidated",
        actor: str = "system",
        superseding_claim_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        if new_status not in {"superseded", "invalidated"}:
            raise ValueError(f"Invalid demotion status: {new_status}")
        if not reason.strip():
            raise ValueError("Demotion reason is required (Article XII Section 4).")
        if new_status == "superseded" and superseding_claim_id is None:
            raise ValueError("superseding_claim_id required for 'superseded' status.")

        claims = self.db.get_blueprint_claims(project)
        claim = next((item for item in claims if int(item["claim_id"]) == int(claim_id)), None)
        if claim is None:
            raise ValueError(f"Claim {claim_id} not found.")
        if claim["status"] != "active":
            raise ValueError(
                f"Claim {claim_id} is '{claim['status']}', only active claims can be demoted."
            )

        if superseding_claim_id is not None:
            superseding = next(
                (item for item in claims if int(item["claim_id"]) == int(superseding_claim_id)),
                None,
            )
            if superseding is None:
                raise ValueError(f"Superseding claim {superseding_claim_id} not found.")
            if superseding["status"] != "active":
                raise ValueError(f"Superseding claim {superseding_claim_id} is not active.")

        old_status = str(claim["status"])
        self.db.update_claim_status(
            int(claim_id),
            new_status,
            supersedes_claim_id=superseding_claim_id,
        )
        self.db.record_lifecycle_event(
            int(claim_id),
            project,
            old_status,
            new_status,
            reason,
            actor=actor,
            superseding_claim_id=superseding_claim_id,
        )
        return {
            "claim_id": int(claim_id),
            "claim_text": str(claim["claim_text"]),
            "old_status": old_status,
            "new_status": new_status,
            "reason": reason,
            "actor": actor,
            "superseding_claim_id": superseding_claim_id,
        }

    def extract_candidates(
        self,
        project: str,
        *,
        stages: Optional[Iterable[str]] = None,
        min_sources: int = 2,
        min_sessions: int = 2,
        min_stages: int = 2,
        limit: int = 20,
    ) -> List[PromotionCandidate]:
        allowed_stages = (
            {stage.strip().lower() for stage in stages if stage.strip()}
            if stages
            else {"intent", "context", "spec", "implementation", "feedback"}
        )
        artifacts = self.db.list_artifacts(project)
        clusters: List[Dict[str, Any]] = []

        for artifact in artifacts:
            if artifact.stage not in allowed_stages:
                continue
            statements = _extract_candidate_statements(artifact.content)
            if not statements:
                continue
            for statement in statements:
                canonical_claim = _canonical_claim(statement)
                normalized = _normalize_statement(statement)
                if not normalized:
                    continue
                source_ref = (artifact.session_id, artifact.stage)
                if canonical_claim:
                    canonical_norm = _normalize_statement(canonical_claim)
                    matched = False
                    for cluster in clusters:
                        if cluster.get("canonical_norm") == canonical_norm:
                            cluster["texts"].append(statement)
                            cluster["sources"].add(source_ref)
                            cluster["sessions"].add(artifact.session_id)
                            cluster["stages"].add(artifact.stage)
                            matched = True
                            break
                    if not matched:
                        clusters.append(
                            {
                                "representative": canonical_claim,
                                "representative_norm": canonical_norm,
                                "canonical_norm": canonical_norm,
                                "texts": [statement],
                                "sources": {source_ref},
                                "sessions": {artifact.session_id},
                                "stages": {artifact.stage},
                            }
                        )
                    continue
                best_idx: Optional[int] = None
                best_score = 0.0
                for idx, cluster in enumerate(clusters):
                    score = self._statement_similarity(normalized, cluster["representative_norm"])
                    if score > best_score:
                        best_idx = idx
                        best_score = score

                if best_idx is None or best_score < 0.82:
                    clusters.append(
                        {
                            "representative": statement,
                            "representative_norm": normalized,
                            "texts": [statement],
                            "sources": {source_ref},
                            "sessions": {artifact.session_id},
                            "stages": {artifact.stage},
                        }
                    )
                    continue

                cluster = clusters[best_idx]
                cluster["texts"].append(statement)
                cluster["sources"].add(source_ref)
                cluster["sessions"].add(artifact.session_id)
                cluster["stages"].add(artifact.stage)
                if len(statement) < len(cluster["representative"]):
                    cluster["representative"] = statement
                    cluster["representative_norm"] = normalized

        candidates: List[PromotionCandidate] = []
        for cluster in clusters:
            support_count = len(cluster["sources"])
            session_count = len(cluster["sessions"])
            stage_count = len(cluster["stages"])
            if (
                support_count < min_sources
                or session_count < min_sessions
                or stage_count < min_stages
            ):
                continue
            claim_text = cluster["representative"] if cluster.get("canonical_norm") else _choose_claim_text(cluster["texts"])
            candidates.append(
                PromotionCandidate(
                    claim_text=claim_text,
                    source_refs=sorted(cluster["sources"]),
                    support_count=support_count,
                    session_count=session_count,
                    stage_count=stage_count,
                    suggested_classification=_suggest_classification(claim_text),
                )
            )

        candidates.sort(
            key=lambda item: (
                -item.session_count,
                -item.stage_count,
                -item.support_count,
                len(item.claim_text),
            )
        )
        return candidates[: max(1, limit)]

    def _load_sources(
        self, project: str, source_refs: List[Tuple[str, str]]
    ) -> List[Dict[str, Any]]:
        rows: List[Dict[str, Any]] = []
        for session_id, stage in source_refs:
            artifact_id = self.db.get_artifact_id(project, session_id, stage)
            if artifact_id is None:
                continue
            record = self.db.load_artifact(project, session_id, stage)
            rows.append(
                {
                    "artifact_id": artifact_id,
                    "session_id": session_id,
                    "stage": stage,
                    "idse_id": record.idse_id,
                    "content_hash": record.content_hash,
                    "semantic_fingerprint": record.semantic_fingerprint,
                    "created_at": record.created_at,
                    "snippet": _extract_meaningful_sentence(record.content),
                }
            )
        return rows

    def _load_feedback(self, project: str, session_ids: Iterable[str]) -> List[Dict[str, Any]]:
        rows: List[Dict[str, Any]] = []
        for session_id in session_ids:
            artifact_id = self.db.get_artifact_id(project, session_id, "feedback")
            if artifact_id is None:
                continue
            record = self.db.load_artifact(project, session_id, "feedback")
            rows.append(
                {
                    "artifact_id": artifact_id,
                    "session_id": session_id,
                    "idse_id": record.idse_id,
                    "content": record.content,
                    "created_at": record.created_at,
                }
            )
        return rows

    @staticmethod
    def _max_pairwise_similarity(snippets: List[str], fingerprints: List[str]) -> float:
        if len(snippets) < 2 and len(fingerprints) < 2:
            return 0.0
        if len(fingerprints) >= 2:
            for idx, left in enumerate(fingerprints):
                for right in fingerprints[idx + 1 :]:
                    if left == right:
                        return 1.0
        best = 0.0
        for idx, left in enumerate(snippets):
            for right in snippets[idx + 1 :]:
                ratio = SequenceMatcher(None, left, right).ratio()
                if ratio > best:
                    best = ratio
        return best

    @staticmethod
    def _statement_similarity(left: str, right: str) -> float:
        if not left or not right:
            return 0.0
        ratio = SequenceMatcher(None, left, right).ratio()
        left_tokens: Set[str] = set(left.split())
        right_tokens: Set[str] = set(right.split())
        union = left_tokens | right_tokens
        if not union:
            return ratio
        jaccard = len(left_tokens & right_tokens) / len(union)
        return (0.7 * ratio) + (0.3 * jaccard)


def _extract_meaningful_sentence(content: str) -> str:
    for line in content.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("- "):
            stripped = stripped[2:].strip()
        if "[REQUIRES INPUT]" in stripped:
            continue
        if len(stripped) >= 20:
            return re.sub(r"\s+", " ", stripped)
    compact = re.sub(r"\s+", " ", content).strip()
    return compact[:240]


def _extract_candidate_statements(content: str) -> List[str]:
    statements: List[str] = []
    seen: Set[str] = set()
    for raw in content.splitlines():
        stripped = raw.strip()
        if not stripped:
            continue
        if stripped.startswith("#") or stripped.startswith("```") or stripped.startswith("|"):
            continue
        if stripped in {"---", "***"}:
            continue
        if stripped.startswith("- "):
            stripped = stripped[2:].strip()
        if stripped.startswith("* "):
            stripped = stripped[2:].strip()
        stripped = re.sub(r"^\d+\.\s+", "", stripped).strip()
        compact = re.sub(r"\s+", " ", stripped)
        lowered = compact.lower()
        if "[requires input]" in lowered:
            continue
        if lowered.startswith("task ") or lowered.startswith("phase "):
            continue
        if "owner:" in lowered and "deps:" in lowered:
            continue
        if compact.count("`") >= 4:
            continue
        if _is_boilerplate_statement(compact):
            continue
        if len(compact) < 32 or len(compact) > 280:
            continue
        if len(compact.split()) < 6:
            continue
        norm = _normalize_statement(compact)
        if norm in seen:
            continue
        seen.add(norm)
        statements.append(compact)
    return statements


def _normalize_statement(text: str) -> str:
    lowered = text.lower()
    lowered = re.sub(r"[^a-z0-9\s]", " ", lowered)
    lowered = re.sub(r"\s+", " ", lowered).strip()
    if not lowered:
        return ""
    stopwords = {
        "the",
        "a",
        "an",
        "and",
        "or",
        "to",
        "of",
        "for",
        "in",
        "on",
        "with",
        "by",
        "is",
        "are",
        "be",
        "as",
        "that",
        "this",
        "it",
    }
    tokens = [token for token in lowered.split() if token not in stopwords]
    return " ".join(tokens)


def _choose_claim_text(texts: List[str]) -> str:
    if not texts:
        return ""
    cleaned = sorted({re.sub(r"\s+", " ", t).strip() for t in texts if t.strip()}, key=len)
    return cleaned[0] if cleaned else ""


def _suggest_classification(claim_text: str) -> str:
    lowered = claim_text.lower()
    if any(word in lowered for word in ["owner", "ownership", "agent", "responsible"]):
        return "ownership_rule"
    if any(word in lowered for word in ["boundary", "scope", "out of scope", "in scope"]):
        return "boundary"
    if any(word in lowered for word in ["must", "never", "required", "default", "authoritative"]):
        return "invariant"
    return "non_negotiable_constraint"


def _canonical_claim(text: str) -> Optional[str]:
    lowered = text.lower()

    has_docs_os = any(
        phrase in lowered
        for phrase in [
            "documentation os",
            "design-time documentation os",
            "design time documentation os",
            "design-time cognition",
        ]
    )
    has_orchestrator = any(token in lowered for token in ["idse orchestrator", "orchestrator"])
    if has_docs_os and has_orchestrator:
        return "IDSE Orchestrator is the design-time Documentation OS for project intent and delivery."

    has_sqlite = "sqlite" in lowered
    has_storage = any(word in lowered for word in ["storage", "backend", "store"])
    has_authority = any(word in lowered for word in ["authoritative", "default", "core", "source of truth"])
    if has_sqlite and has_storage and has_authority:
        return "SQLite is the authoritative storage backend for project artifacts."

    has_notion = "notion" in lowered
    has_sync = any(word in lowered for word in ["sync", "projection", "view-layer", "view layer", "target"])
    not_source = any(
        phrase in lowered
        for phrase in [
            "not source",
            "not authoritative",
            "never source",
            "sync targets only",
            "projection only",
        ]
    )
    if has_notion and has_sync and not_source:
        return "Notion is a sync target and not a source of truth."

    mentions_storage_sync = any(
        phrase in lowered
        for phrase in [
            "storage_backend",
            "sync_backend",
            "storage and sync",
            "storage/sync",
            "storage sync",
        ]
    )
    decoupled = any(word in lowered for word in ["split", "decoupled", "independent", "separate"])
    if mentions_storage_sync and decoupled:
        return "Storage backend and sync backend are decoupled concerns."

    return None


def _is_boilerplate_statement(text: str) -> bool:
    lowered = text.lower()
    boilerplate_contains = (
        "derive tasks directly from the implementation plan",
        "keep tasks independent and testable",
        "note owner, dependencies, and acceptance",
        "these tasks guide the ide/development team",
        "this plan serves as both an implementation plan",
        "product requirements document (prd)",
        "it merges the product vision",
        "canonical artifact of the idse pipeline",
        "must be validated via `idse validate`",
        "this artifact was automatically generated",
        "please populate this document according to idse guidelines",
    )
    if any(fragment in lowered for fragment in boilerplate_contains):
        return True

    if lowered.startswith("task ") or lowered.startswith("phase "):
        return True
    if lowered.startswith("owner:") or lowered.startswith("deps:"):
        return True
    return False


def _has_contradiction(content: str) -> bool:
    lowered = content.lower()
    explicit_markers = (
        "[contradiction]",
        "contradicted_by_feedback",
        "unresolved contradiction",
        "promotion denied",
    )
    if any(marker in lowered for marker in explicit_markers):
        return True

    # Match explicit contradiction statements while avoiding false positives
    # in explanatory prose (for example "contradiction/reinforcement flags").
    sentence_markers = (
        r"\bthis\s+contradicts\b",
        r"\bclaim\s+contradicts\b",
        r"\bwas\s+rejected\b",
        r"\bis\s+rejected\b",
        r"\breject(?:ed|s)\s+this\s+claim\b",
    )
    return any(re.search(pattern, lowered) for pattern in sentence_markers)


def _parse_dt(value: str) -> datetime:
    try:
        return datetime.fromisoformat(value)
    except Exception:
        return datetime.now()
