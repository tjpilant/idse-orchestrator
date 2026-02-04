from __future__ import annotations

from pathlib import Path
from typing import Dict, Iterable, List, Optional

from .artifact_database import ArtifactDatabase
from .design_store import DesignStoreFilesystem


class FileViewGenerator:
    """Generate IDE-friendly markdown views from SQLite artifacts."""

    def __init__(self, db_path: Optional[Path] = None, idse_root: Optional[Path] = None):
        if idse_root is None:
            from .project_workspace import ProjectWorkspace

            manager = ProjectWorkspace()
            idse_root = manager.idse_root

        self.idse_root = Path(idse_root)
        self.projects_root = self.idse_root / "projects"
        self.db = ArtifactDatabase(db_path=db_path, idse_root=self.idse_root)

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
