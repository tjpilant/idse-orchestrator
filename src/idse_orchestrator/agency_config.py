from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional, Dict


class AgencyConfig:
    """Unified config loader: ~/.idseconfig.json → .idse/config.json → env vars → defaults."""

    def __init__(self, workspace_root: Optional[Path] = None):
        self.workspace_root = workspace_root
        self._config = self._load()

    @property
    def agency_url(self) -> Optional[str]:
        return self._config.get("agency_url")

    @property
    def client_id(self) -> Optional[str]:
        return self._config.get("client_id")

    @property
    def project_id(self) -> Optional[str]:
        return self._config.get("project_id")

    def set_project_id(self, project_id: str) -> None:
        self._config["project_id"] = project_id
        self._config["last_sync"] = _now_iso()
        self._persist_workspace_config()

    def _load(self) -> Dict:
        config: Dict = {"agency_url": "http://localhost:8000", "client_id": None, "project_id": None}

        home_path = Path.home() / ".idseconfig.json"
        _merge_json_file(config, home_path)

        workspace_path = self._workspace_config_path()
        if workspace_path:
            _merge_json_file(config, workspace_path)

        env_agency_url = os.getenv("IDSE_AGENCY_URL") or os.getenv("AGENCY_URL")
        env_client_id = os.getenv("IDSE_CLIENT_ID")
        env_project_id = os.getenv("IDSE_PROJECT_ID")

        if env_agency_url:
            config["agency_url"] = env_agency_url
        if env_client_id:
            config["client_id"] = env_client_id
        if env_project_id:
            config["project_id"] = env_project_id

        return config

    def _workspace_config_path(self) -> Optional[Path]:
        if self.workspace_root:
            return self.workspace_root / ".idse" / "config.json"

        try:
            from .project_workspace import ProjectWorkspace

            manager = ProjectWorkspace()
            return manager.idse_root / "config.json"
        except Exception:
            return None

    def _persist_workspace_config(self) -> None:
        path = self._workspace_config_path()
        if not path:
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        existing = {}
        if path.exists():
            try:
                existing = json.loads(path.read_text())
            except json.JSONDecodeError:
                existing = {}
        existing.update(self._config)
        path.write_text(json.dumps(existing, indent=2))


def _merge_json_file(config: Dict, path: Path) -> None:
    if not path.exists():
        return
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError:
        return
    config.update({k: v for k, v in data.items() if v is not None})


def _now_iso() -> str:
    from datetime import datetime

    return datetime.now().isoformat()
