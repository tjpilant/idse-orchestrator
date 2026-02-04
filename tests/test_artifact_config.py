import json
from pathlib import Path

from idse_orchestrator.artifact_config import ArtifactConfig
from idse_orchestrator.design_store import DesignStoreFilesystem


def test_artifact_config_filesystem_backend(tmp_path: Path):
    config_path = tmp_path / "idseconfig.json"
    config_path.write_text(
        json.dumps({"artifact_backend": "filesystem", "base_path": str(tmp_path / ".idse")})
    )

    config = ArtifactConfig(config_path)
    store = config.get_design_store()

    assert isinstance(store, DesignStoreFilesystem)
    assert store.idse_root == tmp_path / ".idse"

