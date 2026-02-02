import json
import os
from pathlib import Path

from idse_orchestrator.agency_config import AgencyConfig


def test_agency_config_precedence(tmp_path: Path, monkeypatch):
    home = tmp_path / "home"
    workspace = tmp_path / "workspace"
    home.mkdir()
    workspace.mkdir()

    monkeypatch.setenv("HOME", str(home))

    home_cfg = home / ".idseconfig.json"
    home_cfg.write_text(json.dumps({"agency_url": "https://home.example", "client_id": "home"}))

    ws_cfg_dir = workspace / ".idse"
    ws_cfg_dir.mkdir()
    ws_cfg = ws_cfg_dir / "config.json"
    ws_cfg.write_text(json.dumps({"agency_url": "https://workspace.example", "project_id": "ws"}))

    monkeypatch.setenv("IDSE_AGENCY_URL", "https://env.example")
    monkeypatch.setenv("IDSE_CLIENT_ID", "env-client")

    cfg = AgencyConfig(workspace_root=workspace)

    assert cfg.agency_url == "https://env.example"
    assert cfg.client_id == "env-client"
    assert cfg.project_id == "ws"
