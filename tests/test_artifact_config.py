import json
from pathlib import Path

from idse_orchestrator.artifact_config import ArtifactConfig
from idse_orchestrator.design_store import DesignStoreFilesystem
from idse_orchestrator.design_store_sqlite import DesignStoreSQLite


def test_artifact_config_filesystem_backend(tmp_path: Path):
    config_path = tmp_path / "idseconfig.json"
    config_path.write_text(
        json.dumps({"storage_backend": "filesystem", "base_path": str(tmp_path / ".idse")})
    )

    config = ArtifactConfig(config_path)
    store = config.get_design_store()

    assert isinstance(store, DesignStoreFilesystem)
    assert store.idse_root == tmp_path / ".idse"


def test_artifact_config_sqlite_backend(tmp_path: Path):
    db_path = tmp_path / ".idse" / "idse.db"
    config_path = tmp_path / "idseconfig.json"
    config_path.write_text(
        json.dumps({"storage_backend": "sqlite", "sqlite": {"db_path": str(db_path)}})
    )

    from idse_orchestrator.artifact_database import ArtifactDatabase

    ArtifactDatabase(db_path=db_path, allow_create=True)
    config = ArtifactConfig(config_path)
    store = config.get_design_store()

    assert isinstance(store, DesignStoreSQLite)
    assert store.db.db_path == db_path


def test_artifact_config_default_backend_sqlite(tmp_path: Path):
    config_path = tmp_path / "idseconfig.json"
    config = ArtifactConfig(config_path)
    assert config.get_storage_backend() == "sqlite"


def test_notion_sync_does_not_override_sqlite_storage(tmp_path: Path):
    config_path = tmp_path / "idseconfig.json"
    config_path.write_text(json.dumps({"sync_backend": "notion"}))

    config = ArtifactConfig(config_path)
    assert config.get_storage_backend() == "sqlite"
    assert config.get_sync_backend() == "notion"


def test_legacy_artifact_backend_notion_maps_to_sync_only(tmp_path: Path):
    config_path = tmp_path / "idseconfig.json"
    config_path.write_text(json.dumps({"artifact_backend": "notion"}))

    config = ArtifactConfig(config_path)
    assert config.get_storage_backend() == "sqlite"
    assert config.get_sync_backend() == "notion"


def test_config_resolution_prefers_local_over_global(tmp_path: Path, monkeypatch):
    """Test that .idse/.idseconfig.json takes priority over ~/.idseconfig.json"""
    monkeypatch.chdir(tmp_path)

    # Create global config
    global_config = tmp_path / "home" / ".idseconfig.json"
    global_config.parent.mkdir(parents=True, exist_ok=True)
    global_config.write_text(json.dumps({
        "sync_backend": "filesystem",
        "notion": {"database_id": "global-db-id"}
    }))

    # Create local config
    local_config = tmp_path / ".idse" / ".idseconfig.json"
    local_config.parent.mkdir(parents=True, exist_ok=True)
    local_config.write_text(json.dumps({
        "sync_backend": "notion",
        "notion": {"database_id": "local-db-id"}
    }))

    # Patch DEFAULT_PATH to use our test global config
    monkeypatch.setattr(ArtifactConfig, "DEFAULT_PATH", global_config)

    # Load config without explicit path
    config = ArtifactConfig()

    # Should load local config, not global
    assert config.config_path == local_config
    assert config.get_sync_backend() == "notion"
    assert config.config["notion"]["database_id"] == "local-db-id"


def test_config_resolution_falls_back_to_global(tmp_path: Path, monkeypatch):
    """Test that ~/.idseconfig.json is used when no local config exists"""
    monkeypatch.chdir(tmp_path)

    # Create global config only (no .idse/.idseconfig.json)
    global_config = tmp_path / "home" / ".idseconfig.json"
    global_config.parent.mkdir(parents=True, exist_ok=True)
    global_config.write_text(json.dumps({
        "sync_backend": "filesystem",
        "notion": {"database_id": "global-db-id"}
    }))

    # Patch DEFAULT_PATH to use our test global config
    monkeypatch.setattr(ArtifactConfig, "DEFAULT_PATH", global_config)

    # Load config without explicit path
    config = ArtifactConfig()

    # Should load global config
    assert config.config_path == global_config
    assert config.get_sync_backend() == "filesystem"
    assert config.config["notion"]["database_id"] == "global-db-id"


def test_explicit_config_path_overrides_resolution(tmp_path: Path, monkeypatch):
    """Test that explicit --config path takes highest priority"""
    monkeypatch.chdir(tmp_path)

    # Create all three configs
    explicit_config = tmp_path / "custom" / "config.json"
    explicit_config.parent.mkdir(parents=True, exist_ok=True)
    explicit_config.write_text(json.dumps({"sync_backend": "sqlite"}))

    local_config = tmp_path / ".idse" / ".idseconfig.json"
    local_config.parent.mkdir(parents=True, exist_ok=True)
    local_config.write_text(json.dumps({"sync_backend": "notion"}))

    global_config = tmp_path / "home" / ".idseconfig.json"
    global_config.parent.mkdir(parents=True, exist_ok=True)
    global_config.write_text(json.dumps({"sync_backend": "filesystem"}))

    monkeypatch.setattr(ArtifactConfig, "DEFAULT_PATH", global_config)

    # Load with explicit path
    config = ArtifactConfig(config_path=explicit_config)

    # Should use explicit path, not local or global
    assert config.config_path == explicit_config
    assert config.get_sync_backend() == "sqlite"
