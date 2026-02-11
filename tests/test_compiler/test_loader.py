from pathlib import Path

from idse_orchestrator.artifact_database import ArtifactDatabase
from idse_orchestrator.compiler.loader import SessionLoader


def test_session_loader_reads_spec_from_sqlite(tmp_path: Path) -> None:
    idse_root = tmp_path / ".idse"
    project = "demo"
    project_root = idse_root / "projects" / project
    project_root.mkdir(parents=True, exist_ok=True)

    db = ArtifactDatabase(idse_root=idse_root)
    db.save_artifact(project, "s1", "spec", "# Specification\n\n## Agent Profile\n\n```yaml\nid: a\nname: A\n```")

    loader = SessionLoader(
        project_root,
        project_name=project,
        backend="sqlite",
        idse_root=idse_root,
    )
    content = loader.load_spec("s1")
    assert "id: a" in content


def test_session_loader_falls_back_to_filesystem_when_sqlite_unavailable(tmp_path: Path) -> None:
    idse_root = tmp_path / ".idse"
    project = "demo"
    project_root = idse_root / "projects" / project
    spec_path = project_root / "sessions" / "s1" / "specs" / "spec.md"
    spec_path.parent.mkdir(parents=True, exist_ok=True)
    spec_path.write_text("# Specification\n\n## Agent Profile\n\n```yaml\nid: fs\nname: FS\n```")

    loader = SessionLoader(
        project_root,
        project_name=project,
        backend="sqlite",
        idse_root=idse_root,
    )
    content = loader.load_spec("s1")
    assert "id: fs" in content
