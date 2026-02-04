from __future__ import annotations

from pathlib import Path
from typing import Dict, Iterable, List, Optional
import json

from .artifact_database import ArtifactDatabase
from .design_store import DesignStoreFilesystem
from .session_metadata import SessionMetadata


class FileToDatabaseMigrator:
    """Migrate file-based IDSE projects into SQLite."""

    def __init__(self, db_path: Optional[Path] = None, idse_root: Optional[Path] = None):
        if idse_root is None:
            from .project_workspace import ProjectWorkspace

            manager = ProjectWorkspace()
            idse_root = manager.idse_root

        self.idse_root = Path(idse_root)
        self.projects_root = self.idse_root / "projects"
        self.db = ArtifactDatabase(db_path=db_path, idse_root=self.idse_root)

    def migrate_project(
        self,
        project_name: Optional[str] = None,
        sessions: Optional[Iterable[str]] = None,
    ) -> Dict[str, List[str]]:
        project_path = self._resolve_project_path(project_name)
        project_name = project_path.name

        summary: Dict[str, List[str]] = {}
        session_ids = list(sessions) if sessions else self._list_sessions(project_path)

        for session_id in session_ids:
            session_path = project_path / "sessions" / session_id
            if not session_path.exists():
                continue
            summary[session_id] = self._migrate_session(project_name, session_path)

        self._migrate_project_state(project_path)
        self._migrate_agent_registry(project_path)
        return summary

    def _resolve_project_path(self, project_name: Optional[str]) -> Path:
        if project_name:
            project_path = self.projects_root / project_name
        else:
            from .project_workspace import ProjectWorkspace

            manager = ProjectWorkspace()
            project_path = manager.get_current_project()
            if not project_path:
                raise FileNotFoundError("No IDSE project found")

        if not project_path.exists():
            raise FileNotFoundError(f"Project not found: {project_path}")

        return project_path

    def _list_sessions(self, project_path: Path) -> List[str]:
        sessions_dir = project_path / "sessions"
        if not sessions_dir.exists():
            return []
        return sorted([p.name for p in sessions_dir.iterdir() if p.is_dir()])

    def _migrate_session(self, project_name: str, session_path: Path) -> List[str]:
        session_id = session_path.name
        stages_written: List[str] = []

        metadata = self._load_session_metadata(session_path)
        self.db.ensure_session(
            project_name,
            session_id,
            name=metadata.get("name"),
            session_type=metadata.get("session_type"),
            description=metadata.get("description"),
            is_blueprint=metadata.get("is_blueprint"),
            parent_session=metadata.get("parent_session"),
            status=metadata.get("status"),
        )
        if metadata.get("collaborators") or metadata.get("tags"):
            self.db.save_session_extras(
                project_name,
                session_id,
                collaborators=metadata.get("collaborators"),
                tags=metadata.get("tags"),
            )

        for stage, (folder, filename) in DesignStoreFilesystem.STAGE_PATHS.items():
            artifact_path = session_path / folder / filename
            if not artifact_path.exists():
                continue
            content = artifact_path.read_text()
            self.db.save_artifact(project_name, session_id, stage, content)
            stages_written.append(stage)

        return stages_written

    def _load_session_metadata(self, session_path: Path) -> Dict[str, Optional[str]]:
        metadata_file = session_path / "metadata" / "session.json"
        if metadata_file.exists():
            try:
                meta = SessionMetadata.load(session_path)
            except Exception:
                meta = None
            if meta:
                return {
                    "name": meta.name,
                    "session_type": meta.session_type,
                    "description": meta.description,
                    "is_blueprint": meta.is_blueprint,
                    "parent_session": meta.parent_session,
                    "status": meta.status,
                    "collaborators": [c.to_dict() for c in meta.collaborators],
                    "tags": meta.tags,
                }

        return {
            "name": session_path.name,
            "session_type": "blueprint" if session_path.name == "__blueprint__" else "feature",
            "description": None,
            "is_blueprint": session_path.name == "__blueprint__",
            "parent_session": None if session_path.name == "__blueprint__" else "__blueprint__",
            "status": "draft",
            "collaborators": [],
            "tags": [],
        }

    def _migrate_project_state(self, project_path: Path) -> None:
        state_file = project_path / "session_state.json"
        if not state_file.exists():
            return
        try:
            state = json.loads(state_file.read_text())
        except json.JSONDecodeError:
            return
        project_name = project_path.name
        session_id = state.get("session_id")
        if session_id:
            self.db.save_session_state(project_name, session_id, state)
        else:
            self.db.save_state(project_name, state)

    def _migrate_agent_registry(self, project_path: Path) -> None:
        registry_file = project_path / "agent_registry.json"
        if not registry_file.exists():
            return
        try:
            registry = json.loads(registry_file.read_text())
        except json.JSONDecodeError:
            return
        project_name = project_path.name
        self.db.save_agent_registry(project_name, registry)
