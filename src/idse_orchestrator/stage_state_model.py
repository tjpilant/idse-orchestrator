"""
Stage State Model

Manages session_state.json for tracking pipeline stage progress.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime


class StageStateModel:
    """Tracks IDSE pipeline stage progression and sync state."""

    STAGE_NAMES = ["intent", "context", "spec", "plan", "tasks", "implementation", "feedback"]

    def __init__(
        self,
        project_path: Optional[Path] = None,
        store=None,
        project_name: Optional[str] = None,
        session_id: Optional[str] = None,
    ):
        """
        Initialize StageStateModel.

        Args:
            project_path: Path to project directory. If None, auto-detects from cwd.
        """
        self.project_path = project_path
        self.store = store
        self.project_name = project_name
        self.session_id = session_id
        if project_path:
            self.state_file = project_path / "session_state.json"
        else:
            self.state_file = None

    def init_state(self, project_name: str, session_id: str, is_blueprint: bool = False) -> Dict:
        """
        Initialize session_state.json with default values.

        Args:
            project_name: Name of the project
            session_id: Session identifier (e.g., "session-1234567890")
            is_blueprint: Whether this is a blueprint session

        Returns:
            Initial state dictionary
        """
        self.project_name = project_name
        self.session_id = session_id
        if not self.state_file and not self.store:
            raise ValueError("Project path not set")

        state = {
            "project_name": project_name,
            "session_id": session_id,
            "is_blueprint": is_blueprint,
            "stages": {stage: "pending" for stage in self.STAGE_NAMES},
            "last_sync": None,
            "validation_status": "unknown",
            "created_at": datetime.now().isoformat(),
        }

        self._write_state(state)
        return state

    def update_stage(self, stage: str, status: str) -> None:
        """
        Update the status of a pipeline stage.

        Args:
            stage: Stage name (intent, context, spec, plan, tasks, implementation, feedback)
            status: New status (pending, in_progress, completed)
        """
        if stage not in self.STAGE_NAMES:
            raise ValueError(f"Unknown stage: {stage}")

        if status not in ["pending", "in_progress", "completed"]:
            raise ValueError(f"Invalid status: {status}")

        state = self._read_state()
        state["stages"][stage] = status
        self._write_state(state)

    def set_validation_status(self, status: str) -> None:
        state = self._read_state()
        state["validation_status"] = status
        self._write_state(state)

    def get_current_stage(self) -> Optional[str]:
        """
        Get the current active stage.

        Returns:
            Stage name or None if all completed
        """
        state = self._read_state()

        for stage in self.STAGE_NAMES:
            if state["stages"][stage] != "completed":
                return stage

        return None

    def mark_synced(self, timestamp: Optional[str] = None) -> None:
        """
        Update last sync timestamp.

        Called after DesignStore-backed operations to record when state
        was last persisted through the store.

        Args:
            timestamp: ISO format timestamp. Defaults to now.
        """
        state = self._read_state()
        state["last_sync"] = timestamp or datetime.now().isoformat()
        self._write_state(state)

    def get_status(self, project_name: Optional[str] = None) -> Dict:
        """
        Get current project status.

        Args:
            project_name: Optional project name (auto-detects if None)

        Returns:
            Status dictionary with project info and stage progression
        """
        if not self.state_file or not self.state_file.exists():
            from .project_workspace import ProjectWorkspace

            manager = ProjectWorkspace()
            if project_name:
                project_path = manager.projects_root / project_name
            else:
                project_path = manager.get_current_project()

            if project_path:
                self.state_file = project_path / "session_state.json"
                self.project_name = project_path.name

        if project_name:
            self.project_name = project_name

        if self.store and self.project_name:
            self._resolve_session_id()
            if hasattr(self.store, "load_session_state") and self.session_id:
                return self.store.load_session_state(self.project_name, self.session_id)
            return self.store.load_state(self.project_name)

        if not self.state_file or not self.state_file.exists():
            raise FileNotFoundError("No session_state.json found. Run 'idse init' first.")

        return self._read_state()

    def auto_detect_stage_completion(self, session_path: Path) -> None:
        """
        Auto-detect stage completion based on artifact presence and content.

        Args:
            session_path: Path to session directory
        """
        state = self._read_state()

        artifact_map = {
            "intent": session_path / "intents" / "intent.md",
            "context": session_path / "contexts" / "context.md",
            "spec": session_path / "specs" / "spec.md",
            "plan": session_path / "plans" / "plan.md",
            "tasks": session_path / "tasks" / "tasks.md",
            "implementation": session_path / "implementation" / "README.md",
            "feedback": session_path / "feedback" / "feedback.md",
        }

        for stage, artifact_path in artifact_map.items():
            if artifact_path.exists():
                content = artifact_path.read_text()

                if len(content) > 200 and "[REQUIRES INPUT]" not in content:
                    state["stages"][stage] = "completed"
                elif len(content) > 100:
                    state["stages"][stage] = "in_progress"

        self._write_state(state)

    def _read_state(self) -> Dict:
        """Read state from JSON file."""
        if self.store and self.project_name:
            self._resolve_session_id()
            if hasattr(self.store, "load_session_state") and self.session_id:
                return self.store.load_session_state(self.project_name, self.session_id)
            return self.store.load_state(self.project_name)

        if not self.state_file or not self.state_file.exists():
            raise FileNotFoundError(f"State file not found: {self.state_file}")

        with self.state_file.open("r") as f:
            return json.load(f)

    def _write_state(self, state: Dict) -> None:
        """Write state to JSON file."""
        if self.store and self.project_name:
            self._resolve_session_id()
            if hasattr(self.store, "save_session_state") and self.session_id:
                self.store.save_session_state(self.project_name, self.session_id, state)
            else:
                self.store.save_state(self.project_name, state)
            if self.state_file:
                self._write_state_file(state)
            return

        if not self.state_file:
            raise ValueError("State file path not set")

        self.state_file.parent.mkdir(parents=True, exist_ok=True)

        with self.state_file.open("w") as f:
            json.dump(state, f, indent=2)

    def _write_state_file(self, state: Dict) -> None:
        if not self.state_file:
            return
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        with self.state_file.open("w") as f:
            json.dump(state, f, indent=2)

    def refresh_state_file(self) -> None:
        state = self._read_state()
        if self.session_id:
            expected_blueprint = self.session_id == "__blueprint__"
            if state.get("session_id") != self.session_id or state.get("is_blueprint") != expected_blueprint:
                state["session_id"] = self.session_id
                state["is_blueprint"] = expected_blueprint
                self._write_state(state)
        self._write_state_file(state)

    def _resolve_session_id(self) -> None:
        if self.session_id or not self.project_path:
            return
        try:
            from .session_graph import SessionGraph

            self.session_id = SessionGraph(self.project_path).get_current_session()
        except Exception:
            return
