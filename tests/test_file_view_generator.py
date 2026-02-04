from pathlib import Path

from idse_orchestrator.artifact_database import ArtifactDatabase
from idse_orchestrator.file_view_generator import FileViewGenerator


def test_file_view_generator_session(tmp_path: Path) -> None:
    idse_root = tmp_path / ".idse"
    db = ArtifactDatabase(idse_root=idse_root)

    project = "demo"
    session = "s1"
    db.save_artifact(project, session, "intent", "hello from db")

    generator = FileViewGenerator(idse_root=idse_root)
    written = generator.generate_session(project, session)

    intent_path = (
        idse_root / "projects" / project / "sessions" / session / "intents" / "intent.md"
    )
    assert intent_path in written
    assert intent_path.read_text() == "hello from db"


def test_file_view_generator_project(tmp_path: Path) -> None:
    idse_root = tmp_path / ".idse"
    db = ArtifactDatabase(idse_root=idse_root)

    project = "demo"
    db.save_artifact(project, "s1", "intent", "s1 intent")
    db.save_artifact(project, "s2", "intent", "s2 intent")

    generator = FileViewGenerator(idse_root=idse_root)
    results = generator.generate_project(project, stages=["intent"])

    assert set(results.keys()) == {"s1", "s2"}
    path_s1 = idse_root / "projects" / project / "sessions" / "s1" / "intents" / "intent.md"
    path_s2 = idse_root / "projects" / project / "sessions" / "s2" / "intents" / "intent.md"
    assert path_s1.exists()
    assert path_s2.exists()
