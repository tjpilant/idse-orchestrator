import json
from pathlib import Path

from idse_orchestrator.artifact_config import ArtifactConfig
from idse_orchestrator.design_store import DesignStoreFilesystem
from idse_orchestrator.design_store_sqlite import DesignStoreSQLite


def test_artifact_config_filesystem_backend(tmp_path: Path):
    config_path = tmp_path / "idseconfig.json"
    config_path.write_text(
        json.dumps({"artifact_backend": "filesystem", "base_path": str(tmp_path / ".idse")})
    )

    config = ArtifactConfig(config_path)
    store = config.get_design_store()

    assert isinstance(store, DesignStoreFilesystem)
    assert store.idse_root == tmp_path / ".idse"


def test_artifact_config_sqlite_backend(tmp_path: Path):
    db_path = tmp_path / ".idse" / "idse.db"
    config_path = tmp_path / "idseconfig.json"
    config_path.write_text(
        json.dumps({"artifact_backend": "sqlite", "sqlite": {"db_path": str(db_path)}})
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
    assert config.get_backend() == "sqlite"
