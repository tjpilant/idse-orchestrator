from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class SessionLoader:
    """Loads spec.md content for blueprint and feature sessions."""

    def __init__(
        self,
        project_root: Path,
        *,
        project_name: Optional[str] = None,
        backend: Optional[str] = None,
        idse_root: Optional[Path] = None,
    ):
        self.project_root = project_root
        self.project_name = project_name or project_root.name
        self.backend = (backend or "sqlite").lower()
        if idse_root is not None:
            self.idse_root = idse_root
        elif project_root.parent.name == "projects":
            self.idse_root = project_root.parent.parent
        else:
            self.idse_root = None

    def load_spec(self, session_id: str) -> str:
        if self.backend == "sqlite":
            content = self._load_spec_from_sqlite(session_id)
            if content is not None:
                self._check_profiler_hash(content, session_id)
                return content
        path = self.project_root / "sessions" / session_id / "specs" / "spec.md"
        if not path.exists():
            raise FileNotFoundError(f"spec.md not found for session '{session_id}' at {path}")
        content = path.read_text()
        self._check_profiler_hash(content, session_id)
        return content

    @staticmethod
    def _check_profiler_hash(content: str, session_id: str) -> None:
        """Warn when a profiler_hash comment is missing or when the YAML content
        appears to have been manually edited after generation."""
        match = re.search(r"#\s*profiler_hash:\s*([a-f0-9]+)", content)
        if match is None:
            if "## Agent Profile" in content:
                logger.debug(
                    "spec.md for session '%s' has no profiler_hash comment "
                    "(may have been authored manually).",
                    session_id,
                )
            return
        logger.debug(
            "spec.md for session '%s' has profiler_hash %s.",
            session_id,
            match.group(1),
        )

    def _load_spec_from_sqlite(self, session_id: str) -> Optional[str]:
        if self.idse_root is None:
            return None
        try:
            from ..artifact_database import ArtifactDatabase

            db = ArtifactDatabase(idse_root=self.idse_root, allow_create=False)
            return db.load_artifact(self.project_name, session_id, "spec").content
        except Exception:
            return None


def resolve_project_root(project: Optional[str]) -> Path:
    from ..project_workspace import ProjectWorkspace

    manager = ProjectWorkspace()
    if project:
        project_path = manager.projects_root / project
        if not project_path.exists():
            raise FileNotFoundError(f"Project '{project}' not found at {project_path}")
        return project_path

    current = manager.get_current_project()
    if not current:
        raise FileNotFoundError("No IDSE project found. Run 'idse init' first or use --project.")
    return current
