from pathlib import Path

from click.testing import CliRunner

import idse_orchestrator
from idse_orchestrator.cli import main


def test_version_exposed():
    assert isinstance(idse_orchestrator.__version__, str)
    assert idse_orchestrator.__version__


def test_cli_version_flag():
    runner = CliRunner()
    result = runner.invoke(main, ["--version"])
    assert result.exit_code == 0


def test_cli_help_flag():
    runner = CliRunner()
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0


def test_cli_export_sqlite(tmp_path):
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        idse_root = Path(".") / ".idse"
        project = "demo"
        (idse_root / "projects" / project).mkdir(parents=True, exist_ok=True)

        from idse_orchestrator.artifact_database import ArtifactDatabase

        db = ArtifactDatabase(idse_root=idse_root)
        db.save_artifact(project, "__blueprint__", "intent", "hello export")

        config_path = Path(".") / ".idseconfig.json"
        config_path.write_text(
            '{"storage_backend": "sqlite", "sqlite": {"db_path": ".idse/idse.db"}}'
        )

        result = runner.invoke(
            main, ["export", "--project", project, "--session", "__blueprint__", "--config", str(config_path)]
        )

        assert result.exit_code == 0
        exported = idse_root / "projects" / project / "sessions" / "__blueprint__" / "intents" / "intent.md"
        assert exported.exists()
        assert exported.read_text() == "hello export"


def test_cli_query_sessions(tmp_path):
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        idse_root = Path(".") / ".idse"
        project = "demo"
        (idse_root / "projects" / project).mkdir(parents=True, exist_ok=True)

        from idse_orchestrator.artifact_database import ArtifactDatabase

        db = ArtifactDatabase(idse_root=idse_root)
        db.save_artifact(project, "__blueprint__", "intent", "hello")
        db.save_artifact(project, "session-1", "intent", "hello")

        config_path = Path(".") / ".idseconfig.json"
        config_path.write_text(
            '{"storage_backend": "sqlite", "sqlite": {"db_path": ".idse/idse.db"}}'
        )

        result = runner.invoke(
            main, ["query", "sessions", "--project", project, "--config", str(config_path)]
        )
        assert result.exit_code == 0
        assert "__blueprint__" in result.output
        assert "session-1" in result.output


def test_cli_artifact_write_sqlite(tmp_path):
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        idse_root = Path(".") / ".idse"
        project = "demo"
        (idse_root / "projects" / project / "sessions" / "__blueprint__").mkdir(parents=True, exist_ok=True)
        (idse_root / "projects" / project / "CURRENT_SESSION").write_text("__blueprint__")

        from idse_orchestrator.artifact_database import ArtifactDatabase

        db = ArtifactDatabase(idse_root=idse_root)
        db.set_current_session(project, "__blueprint__")

        config_path = Path(".") / ".idseconfig.json"
        config_path.write_text(
            '{"storage_backend": "sqlite", "sqlite": {"db_path": ".idse/idse.db"}}'
        )

        result = runner.invoke(
            main,
            ["--backend", "sqlite", "artifact", "write", "--project", project, "--stage", "feedback"],
            input="hello feedback",
        )
        assert result.exit_code == 0

        record = db.load_artifact(project, "__blueprint__", "feedback")
        assert record.content == "hello feedback"

        view_path = idse_root / "projects" / project / "sessions" / "__blueprint__" / "feedback" / "feedback.md"
        assert view_path.exists()
