from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, Dict, List


class DesignStore(ABC):
    @abstractmethod
    def load_artifact(self, project: str, session_id: str, stage: str) -> str:
        raise NotImplementedError

    @abstractmethod
    def save_artifact(self, project: str, session_id: str, stage: str, content: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def list_sessions(self, project: str) -> List[str]:
        raise NotImplementedError

    @abstractmethod
    def load_state(self, project: str) -> Dict:
        raise NotImplementedError

    @abstractmethod
    def save_state(self, project: str, state: Dict) -> None:
        raise NotImplementedError


class DesignStoreFilesystem(DesignStore):
    """Default filesystem implementation. Reads/writes .idse/projects/<project>/."""

    STAGE_PATHS = {
        "intent": ("intents", "intent.md"),
        "context": ("contexts", "context.md"),
        "spec": ("specs", "spec.md"),
        "plan": ("plans", "plan.md"),
        "tasks": ("tasks", "tasks.md"),
        "implementation": ("implementation", "README.md"),
        "feedback": ("feedback", "feedback.md"),
    }

    def __init__(self, idse_root: Path):
        self.idse_root = idse_root
        self.projects_root = self.idse_root / "projects"

    def _project_path(self, project: str) -> Path:
        return self.projects_root / project

    def _session_path(self, project: str, session_id: str) -> Path:
        return self._project_path(project) / "sessions" / session_id

    def _artifact_path(self, project: str, session_id: str, stage: str) -> Path:
        if stage not in self.STAGE_PATHS:
            raise ValueError(f"Unknown stage: {stage}")
        folder, filename = self.STAGE_PATHS[stage]
        return self._session_path(project, session_id) / folder / filename

    def load_artifact(self, project: str, session_id: str, stage: str) -> str:
        path = self._artifact_path(project, session_id, stage)
        if not path.exists():
            raise FileNotFoundError(f"Artifact not found: {path}")
        return path.read_text()

    def save_artifact(self, project: str, session_id: str, stage: str, content: str) -> None:
        path = self._artifact_path(project, session_id, stage)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)

    def list_sessions(self, project: str) -> List[str]:
        sessions_dir = self._project_path(project) / "sessions"
        if not sessions_dir.exists():
            return []
        return sorted([p.name for p in sessions_dir.iterdir() if p.is_dir()])

    def load_state(self, project: str) -> Dict:
        state_file = self._project_path(project) / "session_state.json"
        if not state_file.exists():
            raise FileNotFoundError(f"State file not found: {state_file}")
        return _read_json(state_file)

    def save_state(self, project: str, state: Dict) -> None:
        state_file = self._project_path(project) / "session_state.json"
        state_file.parent.mkdir(parents=True, exist_ok=True)
        _write_json(state_file, state)


def _read_json(path: Path) -> Dict:
    import json

    with path.open("r") as f:
        return json.load(f)


def _write_json(path: Path, data: Dict) -> None:
    import json

    with path.open("w") as f:
        json.dump(data, f, indent=2)
