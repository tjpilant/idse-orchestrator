from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

from .artifact_database import ArtifactDatabase
from .design_store import DesignStore


class DesignStoreSQLite(DesignStore):
    """SQLite-backed DesignStore implementation."""

    def __init__(self, db_path: Optional[Path] = None, idse_root: Optional[Path] = None):
        self.db = ArtifactDatabase(db_path=db_path, idse_root=idse_root)

    def load_artifact(self, project: str, session_id: str, stage: str) -> str:
        record = self.db.load_artifact(project, session_id, stage)
        return record.content

    def save_artifact(self, project: str, session_id: str, stage: str, content: str) -> None:
        self.db.save_artifact(project, session_id, stage, content)

    def list_sessions(self, project: str) -> List[str]:
        return self.db.list_sessions(project)

    def load_state(self, project: str) -> Dict:
        return self.db.load_state(project)

    def save_state(self, project: str, state: Dict) -> None:
        self.db.save_state(project, state)
