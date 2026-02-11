from pathlib import Path

import pytest
import yaml

from idse_orchestrator.compiler import compile_agent_spec
from idse_orchestrator.compiler.errors import ValidationError


def _write_spec(path: Path, yaml_block: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"# Specification\n\n## Agent Profile\n\n```yaml\n{yaml_block}\n```\n"
    )


def test_compile_agent_spec_end_to_end_from_sqlite(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    idse_root = tmp_path / ".idse"
    project = "demo"
    (idse_root / "projects" / project).mkdir(parents=True, exist_ok=True)

    from idse_orchestrator.artifact_database import ArtifactDatabase

    db = ArtifactDatabase(idse_root=idse_root)
    db.save_artifact(
        project,
        "__blueprint__",
        "spec",
        "# Specification\n\n## Agent Profile\n\n```yaml\nid: base\nname: Base Agent\ntools:\n  - sqlite\nruntime_hints:\n  timeout: 30\n```\n",
    )
    db.save_artifact(
        project,
        "feature-a",
        "spec",
        "# Specification\n\n## Agent Profile\n\n```yaml\nid: feature-a\nname: Feature Agent\ntools:\n  - cli\nruntime_hints:\n  retries: 2\n```\n",
    )

    output = compile_agent_spec(
        project=project,
        session_id="feature-a",
        blueprint_id="__blueprint__",
        backend="sqlite",
        dry_run=True,
    )
    data = yaml.safe_load(output)
    assert data["id"] == "feature-a"
    assert data["name"] == "Feature Agent"
    assert data["tools"] == ["cli"]
    assert data["runtime_hints"]["timeout"] == 30
    assert data["runtime_hints"]["retries"] == 2
    assert data["source_session"] == "feature-a"
    assert data["source_blueprint"] == "__blueprint__"


def test_compile_agent_spec_validation_error_when_required_fields_missing(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    idse_root = tmp_path / ".idse"
    project = "demo"
    (idse_root / "projects" / project).mkdir(parents=True, exist_ok=True)

    from idse_orchestrator.artifact_database import ArtifactDatabase

    db = ArtifactDatabase(idse_root=idse_root)
    db.save_artifact(
        project,
        "__blueprint__",
        "spec",
        "# Specification\n\n## Agent Profile\n\n```yaml\ndescription: Base defaults only\n```\n",
    )
    db.save_artifact(
        project,
        "feature-b",
        "spec",
        "# Specification\n\n## Agent Profile\n\n```yaml\ndescription: Missing required fields\n```\n",
    )

    with pytest.raises(ValidationError):
        compile_agent_spec(
            project=project,
            session_id="feature-b",
            blueprint_id="__blueprint__",
            backend="sqlite",
            dry_run=True,
        )
