"""
MCP Client

Handles Machine-to-Cloud Protocol communication with Agency Core backend.
"""

import requests
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime
import json


class MCPClient:
    """Client for syncing with Agency Core via MCP protocol."""

    def __init__(self, agency_url: Optional[str] = None, config_path: Optional[Path] = None):
        """
        Initialize MCP Client.

        Args:
            agency_url: URL of Agency Core backend (e.g., "https://agency.example.com")
            config_path: Path to .idseconfig.json for credentials
        """
        self.config = self._load_config(config_path)
        self.agency_url = agency_url or self.config.get("agency_url") or "http://localhost:8000"
        self.session = requests.Session()

    def push_project(self, project_name: Optional[str] = None, session_override: Optional[str] = None) -> Dict:
        """
        Push local pipeline artifacts to Agency Core.

        Args:
            project_name: Optional project name (auto-detects if None)

        Returns:
            Response dict with sync_id and timestamp
        """
        from .project_manager import ProjectManager

        manager = ProjectManager()
        if project_name:
            project_path = manager.projects_root / project_name
            if not project_path.exists():
                raise ValueError(f"Project '{project_name}' not found at {project_path}")
        else:
            project_path = manager.get_current_project()
            if not project_path:
                raise ValueError("No IDSE project found. Run 'idse init' first or use --project.")

        # Get current session
        session_id = session_override or manager.get_current_session(project_path)
        session_path = project_path / "sessions" / session_id

        # Read all artifacts
        artifacts = self._read_artifacts(session_path)

        # Read session state
        from .state_tracker import StateTracker
        from .session_metadata import SessionMetadata

        tracker = StateTracker(project_path)
        state = tracker.get_status()

        # Read session metadata
        try:
            session_metadata = SessionMetadata.load(session_path)
            metadata_dict = session_metadata.to_dict()
        except FileNotFoundError:
            # Legacy session without metadata
            metadata_dict = {
                "session_id": session_id,
                "session_type": "blueprint" if session_id == "__blueprint__" else "feature",
                "is_blueprint": session_id == "__blueprint__",
                "status": "unknown"
            }

        # Prepare push request
        artifacts_payload = {
            f"{key.replace('.md', '_md')}": value for key, value in artifacts.items()
        }

        project_key = project_name or project_path.name
        project_id = manager.get_project_uuid(project_key) or self.config.get("project_id")
        payload = {
            "project_id": project_id,
            "project_name": project_key,
            "session_id": session_id,
            "session_metadata": metadata_dict,
            "stack": "python",
            "framework": "agency-swarm",
            "artifacts": artifacts_payload,
            "state_json": state,
            "session_state_json": state,
            "timestamp": datetime.now().isoformat(),
        }

        # Send to Agency Core
        response = self.session.post(
            f"{self.agency_url}/sync/push",
            json=payload,
            timeout=30
        )

        response.raise_for_status()

        result = response.json()

        # Update local sync timestamp
        tracker.mark_synced(result.get("timestamp"))

        # Persist project_id for future syncs
        if result.get("project_id"):
            manager.set_project_uuid(project_key, result["project_id"])
            self._save_project_id(result["project_id"])

        return result

    def pull_project(self, project_name: Optional[str] = None, force: bool = False, session_override: Optional[str] = None) -> Dict:
        """
        Pull latest artifacts from Agency Core.

        Args:
            project_name: Optional project name (auto-detects if None)
            force: If True, overwrite local changes without prompting
            session_override: Optional session ID to pull (uses CURRENT_SESSION if None)

        Returns:
            Response dict with artifacts and conflicts (if any)
        """
        from .project_manager import ProjectManager

        manager = ProjectManager()
        if project_name:
            project_path = manager.projects_root / project_name
            if not project_path.exists():
                raise ValueError(f"Project '{project_name}' not found at {project_path}")
        else:
            project_path = manager.get_current_project()
            if not project_path:
                raise ValueError("No IDSE project found. Run 'idse init' first or use --project.")

        project_id = self.config.get("project_id")
        if not project_id:
            raise ValueError("No project_id found. Set it in .idse/config.json or run 'idse sync push' once to store it.")

        # Determine session ID - use override, or CURRENT_SESSION, or default to __blueprint__
        session_id = session_override
        if not session_id:
            session_id = manager.get_current_session(project_path)
        if not session_id:
            session_id = "__blueprint__"

        # Request from Agency Core with session context
        response = self.session.post(
            f"{self.agency_url}/sync/pull",
            json={
                "project_id": project_id,
                "session_id": session_id
            },
        )

        response.raise_for_status()

        return response.json()

    def pull_blueprint(self, project_id: str, session_id: str = "__blueprint__") -> dict:
        """Pull blueprint artifacts from Agency Core."""
        payload = {
            "project_id": project_id,
            "session_id": session_id
        }

        response = self.session.post(
            f"{self.agency_url}/sync/pull",
            json=payload,
            timeout=30
        )
        response.raise_for_status()

        return response.json().get("artifacts", {})

    def apply_pull(self, pull_response: Dict) -> None:
        """
        Apply pulled artifacts to local filesystem.

        Handles both new path-based format (from documents table) and
        legacy *_md format (from projects table).

        Args:
            pull_response: Response from pull_project()
        """
        from .project_manager import ProjectManager

        manager = ProjectManager()
        project_path = manager.get_current_project()

        # Use session_id from response, or fall back to CURRENT_SESSION
        session_id = pull_response.get("session_id") or manager.get_current_session(project_path)
        session_path = project_path / "sessions" / session_id

        artifacts = pull_response.get("artifacts", {})

        # Check if this is new path-based format (paths like "intents/intent.md")
        # or legacy format (keys like "intent_md")
        is_path_based = any("/" in key for key in artifacts.keys())

        if is_path_based:
            # New format: artifacts are keyed by path (e.g., "intents/intent.md")
            for path, content in artifacts.items():
                file_path = session_path / path
                file_path.parent.mkdir(parents=True, exist_ok=True)
                file_path.write_text(content)
        else:
            # Legacy format: artifacts are keyed by *_md suffix
            artifact_map = {
                "intent_md": session_path / "intents" / "intent.md",
                "context_md": session_path / "contexts" / "context.md",
                "spec_md": session_path / "specs" / "spec.md",
                "plan_md": session_path / "plans" / "plan.md",
                "tasks_md": session_path / "tasks" / "tasks.md",
                "implementation_md": session_path / "implementation" / "README.md",
                "feedback_md": session_path / "feedback" / "feedback.md",
            }

            for artifact_key, file_path in artifact_map.items():
                if artifact_key in artifacts:
                    file_path.parent.mkdir(parents=True, exist_ok=True)
                    file_path.write_text(artifacts[artifact_key])

        # Update session state (check both old and new field names)
        state_data = pull_response.get("session_state") or pull_response.get("state_json")
        if state_data:
            from .state_tracker import StateTracker

            tracker = StateTracker(project_path)
            state_file = session_path / "metadata" / "session_state.json"

            state_file.parent.mkdir(parents=True, exist_ok=True)
            with state_file.open("w") as f:
                json.dump(state_data, f, indent=2)

            tracker.mark_synced(pull_response.get("updated_at"))

    def _authenticate(self) -> str:
        """
        Authenticate with Agency Core and get JWT token.

        Returns:
            JWT token string
        """
        # Backend does not require auth yet; placeholder for future JWT support
        return ""

    def _read_artifacts(self, session_path: Path) -> Dict[str, str]:
        """
        Read all artifacts from session directory.

        Args:
            session_path: Path to session directory

        Returns:
            Dictionary mapping artifact names to content
        """
        artifact_map = {
            "meta.md": session_path / "metadata" / "meta.md",
            "intent.md": session_path / "intents" / "intent.md",
            "context.md": session_path / "contexts" / "context.md",
            "spec.md": session_path / "specs" / "spec.md",
            "plan.md": session_path / "plans" / "plan.md",
            "tasks.md": session_path / "tasks" / "tasks.md",
            "implementation.md": session_path / "implementation" / "README.md",
            "feedback.md": session_path / "feedback" / "feedback.md",
        }

        artifacts = {}

        for artifact_name, file_path in artifact_map.items():
            if file_path.exists():
                artifacts[artifact_name] = file_path.read_text()

        return artifacts

    def _load_config(self, config_path: Optional[Path] = None) -> Dict:
        """
        Load configuration from .idseconfig.json.

        Args:
            config_path: Optional path to config file

        Returns:
            Configuration dictionary
        """
        config_candidates = []

        if config_path:
            config_candidates.append(Path(config_path))
        else:
            # Try workspace-level config first
            try:
                from .project_manager import ProjectManager

                manager = ProjectManager()
                config_candidates.append(manager.idse_root / "config.json")
            except Exception:
                pass

            # Then fall back to home directory config
            config_candidates.append(Path.home() / ".idseconfig.json")

        for path in config_candidates:
            if path and path.exists():
                with path.open("r") as f:
                    return json.load(f)

        return {"agency_url": "http://localhost:8000", "client_id": None, "project_id": None}

    def _save_project_id(self, project_id: str) -> None:
        """Persist project_id for future syncs."""
        from .project_manager import ProjectManager

        manager = ProjectManager()
        config_file = manager.idse_root / "config.json"
        config_file.parent.mkdir(parents=True, exist_ok=True)

        config = {}
        if config_file.exists():
            config = json.loads(config_file.read_text())

        config["project_id"] = project_id
        config["last_sync"] = datetime.now().isoformat()
        config["agency_url"] = self.agency_url

        config_file.write_text(json.dumps(config, indent=2))
        self.config.update(config)
