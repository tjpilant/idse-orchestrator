from __future__ import annotations

from pathlib import Path
from typing import Optional


class SessionLoader:
    """Loads spec.md content for blueprint and feature sessions."""

    def __init__(self, project_root: Path):
        self.project_root = project_root

    def load_spec(self, session_id: str) -> str:
        path = self.project_root / "sessions" / session_id / "specs" / "spec.md"
        if not path.exists():
            raise FileNotFoundError(f"spec.md not found for session '{session_id}' at {path}")
        return path.read_text()


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
