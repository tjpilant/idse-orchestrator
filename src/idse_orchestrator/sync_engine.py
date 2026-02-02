"""
Sync Engine

Facade over DesignStore that tracks sync state via StageStateModel.
Backend-agnostic replacement for the former HTTP-based sync engine.
"""

from __future__ import annotations

from typing import Dict, List, Optional
from datetime import datetime

from .design_store import DesignStore
from .stage_state_model import StageStateModel


class SyncEngine:
    """Push/pull artifacts through DesignStore, track sync state."""

    STAGE_NAMES = [
        "intent",
        "context",
        "spec",
        "plan",
        "tasks",
        "implementation",
        "feedback",
    ]

    def __init__(self, store: DesignStore, state_model: StageStateModel):
        self.store = store
        self.state_model = state_model

    def push(self, project: str, session_id: str, artifacts: Dict[str, str]) -> Dict:
        """
        Write artifacts to the DesignStore and update last_sync.

        Args:
            project: Project name
            session_id: Session identifier
            artifacts: Dict mapping stage name to content

        Returns:
            Summary dict with timestamp and stages pushed
        """
        pushed_stages = []
        for stage, content in artifacts.items():
            if stage in self.STAGE_NAMES:
                self.store.save_artifact(project, session_id, stage, content)
                pushed_stages.append(stage)

        timestamp = datetime.now().isoformat()
        self.state_model.mark_synced(timestamp)

        return {
            "timestamp": timestamp,
            "synced_stages": pushed_stages,
            "project": project,
            "session_id": session_id,
        }

    def pull(
        self, project: str, session_id: str, stages: Optional[List[str]] = None
    ) -> Dict[str, str]:
        """
        Read artifacts from the DesignStore.

        Args:
            project: Project name
            session_id: Session identifier
            stages: Optional list of stages to pull. Defaults to all.

        Returns:
            Dict mapping stage name to content
        """
        stages_to_pull = stages or self.STAGE_NAMES
        artifacts = {}
        for stage in stages_to_pull:
            try:
                content = self.store.load_artifact(project, session_id, stage)
                artifacts[stage] = content
            except FileNotFoundError:
                pass

        timestamp = datetime.now().isoformat()
        self.state_model.mark_synced(timestamp)

        return artifacts
