from __future__ import annotations

from pathlib import Path
from typing import Dict, Iterable, List, Optional
import json

from .artifact_database import ArtifactDatabase
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
        sessions = self.db.list_session_metadata(project)
        sessions.sort(key=lambda s: (0 if s["session_id"] == "__blueprint__" else 1, s["created_at"]))

        registry_lines = []
        matrix_rows = []
        for meta in sessions:
            if meta["session_id"] == "__blueprint__":
                registry_lines.append("- `__blueprint__` (THIS SESSION) - Project governance and roadmap")
            else:
                description = meta.get("description") or "Feature session"
                registry_lines.append(f"- `{meta['session_id']}` - {description}")
            matrix_rows.append(
                f"| {meta['session_id']} | {meta['session_type']} | {meta['status']} |"
                f" {meta.get('owner') or 'system'} | {meta['created_at'][:10]} | 0% |"
            )

        registry_section = "\n".join(registry_lines) if registry_lines else "(To be added as sessions are created)"
        matrix_section = "\n".join([
            "| Session ID | Type | Status | Owner | Created | Progress |",
            "|------------|------|--------|-------|---------|----------|",
        ] + matrix_rows)

        content = f"""# {project} - Blueprint Session Meta

## Session Registry

This document tracks all sessions spawned from this Blueprint.

### Active Sessions
{registry_section}

## Session Status Matrix

{matrix_section}

## Lineage Graph

```
__blueprint__ (root)
```

## Governance

This Blueprint defines:
- Project-level intent and vision
- Technical architecture constraints
- Feature roadmap and dependencies
- Session creation rules

All Feature Sessions inherit from this Blueprint's context and specs.

## Feedback Loop

Feedback from Feature Sessions flows upward to inform Blueprint updates.

---
*Last updated: {_now()}*
"""
        blueprint_meta = self.projects_root / project / "sessions" / "__blueprint__" / "metadata" / "meta.md"
        blueprint_meta.parent.mkdir(parents=True, exist_ok=True)
        blueprint_meta.write_text(content)
        return blueprint_meta


def _now() -> str:
    from datetime import datetime

    return datetime.now().isoformat()
