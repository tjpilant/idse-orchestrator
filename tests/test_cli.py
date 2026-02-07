import json
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


def test_cli_session_set_owner_updates_metadata_and_sqlite(tmp_path):
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        idse_root = Path(".") / ".idse"
        project = "demo"
        session_id = "session-1"
        session_dir = idse_root / "projects" / project / "sessions" / session_id
        session_dir.mkdir(parents=True, exist_ok=True)

        metadata_dir = session_dir / "metadata"
        metadata_dir.mkdir(parents=True, exist_ok=True)
        metadata = {
            "session_id": session_id,
            "name": session_id,
            "session_type": "feature",
            "description": None,
            "is_blueprint": False,
            "parent_session": "__blueprint__",
            "related_sessions": [],
            "owner": "system",
            "collaborators": [],
            "tags": [],
            "status": "draft",
            "created_at": "2026-02-07T00:00:00",
            "updated_at": "2026-02-07T00:00:00",
        }
        (metadata_dir / "session.json").write_text(json.dumps(metadata, indent=2))

        from idse_orchestrator.artifact_database import ArtifactDatabase

        db = ArtifactDatabase(idse_root=idse_root)
        db.ensure_session(project, session_id, owner="system", status="draft")

        result = runner.invoke(
            main,
            ["session", "set-owner", session_id, "--project", project, "--owner", "alice"],
        )
        assert result.exit_code == 0

        updated = json.loads((metadata_dir / "session.json").read_text())
        assert updated["owner"] == "alice"

        sessions = db.list_session_metadata(project)
        row = next(s for s in sessions if s["session_id"] == session_id)
        assert row["owner"] == "alice"


def test_cli_session_add_collaborator_updates_metadata_and_sqlite(tmp_path):
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        idse_root = Path(".") / ".idse"
        project = "demo"
        session_id = "session-1"
        session_dir = idse_root / "projects" / project / "sessions" / session_id
        session_dir.mkdir(parents=True, exist_ok=True)

        metadata_dir = session_dir / "metadata"
        metadata_dir.mkdir(parents=True, exist_ok=True)
        metadata = {
            "session_id": session_id,
            "name": session_id,
            "session_type": "feature",
            "description": None,
            "is_blueprint": False,
            "parent_session": "__blueprint__",
            "related_sessions": [],
            "owner": "system",
            "collaborators": [],
            "tags": [],
            "status": "draft",
            "created_at": "2026-02-07T00:00:00",
            "updated_at": "2026-02-07T00:00:00",
        }
        (metadata_dir / "session.json").write_text(json.dumps(metadata, indent=2))

        from idse_orchestrator.artifact_database import ArtifactDatabase

        db = ArtifactDatabase(idse_root=idse_root)
        db.ensure_session(project, session_id, owner="system", status="draft")

        result = runner.invoke(
            main,
            [
                "session",
                "add-collaborator",
                session_id,
                "--project",
                project,
                "--name",
                "bob",
                "--role",
                "reviewer",
            ],
        )
        assert result.exit_code == 0

        updated = json.loads((metadata_dir / "session.json").read_text())
        assert len(updated["collaborators"]) == 1
        assert updated["collaborators"][0]["name"] == "bob"
        assert updated["collaborators"][0]["role"] == "reviewer"

        with db._connect() as conn:
            row = conn.execute(
                """
                SELECT c.name, c.role
                FROM collaborators c
                JOIN sessions s ON c.session_id = s.id
                JOIN projects p ON s.project_id = p.id
                WHERE p.name = ? AND s.session_id = ? AND c.name = ?;
                """,
                (project, session_id, "bob"),
            ).fetchone()
        assert row is not None
        assert row["role"] == "reviewer"


def test_cli_session_set_status_complete_updates_metadata_and_state(tmp_path):
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        idse_root = Path(".") / ".idse"
        project = "demo"
        session_id = "session-1"
        session_dir = idse_root / "projects" / project / "sessions" / session_id
        session_dir.mkdir(parents=True, exist_ok=True)

        metadata_dir = session_dir / "metadata"
        metadata_dir.mkdir(parents=True, exist_ok=True)
        metadata = {
            "session_id": session_id,
            "name": session_id,
            "session_type": "feature",
            "description": None,
            "is_blueprint": False,
            "parent_session": "__blueprint__",
            "related_sessions": [],
            "owner": "system",
            "collaborators": [],
            "tags": [],
            "status": "draft",
            "created_at": "2026-02-07T00:00:00",
            "updated_at": "2026-02-07T00:00:00",
        }
        (metadata_dir / "session.json").write_text(json.dumps(metadata, indent=2))

        from idse_orchestrator.artifact_database import ArtifactDatabase

        db = ArtifactDatabase(idse_root=idse_root)
        db.ensure_session(project, session_id, owner="system", status="draft")

        result = runner.invoke(
            main,
            ["session", "set-status", session_id, "--project", project, "--status", "complete"],
        )
        assert result.exit_code == 0

        updated = json.loads((metadata_dir / "session.json").read_text())
        assert updated["status"] == "complete"

        sessions = db.list_session_metadata(project)
        row = next(s for s in sessions if s["session_id"] == session_id)
        assert row["status"] == "complete"

        state = db.load_session_state(project, session_id)
        assert all(value == "completed" for value in state["stages"].values())
