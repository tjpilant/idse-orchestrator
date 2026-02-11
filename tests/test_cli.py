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
        db.save_artifact(project, session_id, "intent", "## Problem / Opportunity\nx\n## Stakeholders\nx\n## Success Criteria\nx\n")
        db.save_artifact(project, session_id, "context", "## Constraints\nx\n")
        db.save_artifact(project, session_id, "spec", "## Functional Requirements\nx\n")
        db.save_artifact(project, session_id, "plan", "## Plan\nx\n")
        db.save_artifact(project, session_id, "tasks", "## Phase\nx\n")
        db.save_artifact(
            project,
            session_id,
            "implementation",
            "## Architecture\nx\n## What Was Built\nx\n## Validation Reports\nx\n## Deviations from Plan\nnone\n## Component Impact Report\n### Modified Components\n- **CLIInterface** (src/idse_orchestrator/cli.py)\n  - Parent Primitives: CLIInterface\n  - Type: Routing\n  - Changes: Added completion gate\n",
        )
        db.save_artifact(project, session_id, "feedback", "## Feedback\nx\n")
        db.save_session_state(project, session_id, {"project_name": project, "session_id": session_id, "stages": {}})

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


def test_cli_session_set_status_complete_fails_on_placeholder_implementation(tmp_path):
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
        db.save_artifact(
            project,
            session_id,
            "implementation",
            "# Implementation: {{ project_name }}\n\n## Component Impact Report\n### Modified Components\n- **ComponentName** (source_module.py)\n",
        )

        result = runner.invoke(
            main,
            ["session", "set-status", session_id, "--project", project, "--status", "complete"],
        )
        assert result.exit_code != 0
        assert "Cannot mark demo/session-1 complete: validation failed" in result.output


def test_cli_session_set_stage_updates_single_stage_status(tmp_path):
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
                "set-stage",
                session_id,
                "--project",
                project,
                "--stage",
                "implementation",
                "--status",
                "in_progress",
            ],
        )
        assert result.exit_code == 0

        state = db.load_session_state(project, session_id)
        assert state["stages"]["implementation"] == "in_progress"
        assert state["stages"]["intent"] == "pending"


def test_cli_sync_push_reports_partial_failures_without_abort(tmp_path, monkeypatch):
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        idse_root = Path(".") / ".idse"
        project = "demo"
        session_id = "s1"
        (idse_root / "projects" / project / "sessions" / session_id).mkdir(parents=True, exist_ok=True)

        from idse_orchestrator.artifact_database import ArtifactDatabase

        db = ArtifactDatabase(idse_root=idse_root)
        db.save_artifact(project, session_id, "intent", "intent body")
        db.save_artifact(project, session_id, "context", "context body")
        db.save_session_state(
            project,
            session_id,
            {
                "project_name": project,
                "session_id": session_id,
                "is_blueprint": False,
                "stages": {
                    "intent": "pending",
                    "context": "pending",
                    "spec": "pending",
                    "plan": "pending",
                    "tasks": "pending",
                    "implementation": "pending",
                    "feedback": "pending",
                },
                "last_sync": None,
                "validation_status": "unknown",
                "created_at": "2026-02-08T00:00:00",
            },
        )

        class FakeRemoteStore:
            def __init__(self):
                self.last_write_skipped = False

            def save_artifact(self, _project, _session, stage, _content):
                if stage == "context":
                    raise RuntimeError("context push failed")
                self.last_write_skipped = False

        monkeypatch.setattr(
            "idse_orchestrator.artifact_config.ArtifactConfig.get_design_store",
            lambda *_args, **_kwargs: FakeRemoteStore(),
        )

        config_path = Path(".") / ".idseconfig.json"
        config_path.write_text(
            '{"storage_backend":"sqlite","sync_backend":"notion","sqlite":{"db_path":".idse/idse.db"}}'
        )

        result = runner.invoke(
            main,
            [
                "sync",
                "--config",
                str(config_path),
                "push",
                "--project",
                project,
                "--session",
                session_id,
                "--yes",
            ],
        )
        assert result.exit_code == 0
        assert "Failed: context" in result.output
        assert "- context: context push failed" in result.output


def test_cli_sync_pull_reports_partial_failures_without_abort(tmp_path, monkeypatch):
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        idse_root = Path(".") / ".idse"
        project = "demo"
        session_id = "s1"
        (idse_root / "projects" / project / "sessions" / session_id).mkdir(parents=True, exist_ok=True)

        from idse_orchestrator.artifact_database import ArtifactDatabase

        db = ArtifactDatabase(idse_root=idse_root)
        db.save_session_state(
            project,
            session_id,
            {
                "project_name": project,
                "session_id": session_id,
                "is_blueprint": False,
                "stages": {
                    "intent": "pending",
                    "context": "pending",
                    "spec": "pending",
                    "plan": "pending",
                    "tasks": "pending",
                    "implementation": "pending",
                    "feedback": "pending",
                },
                "last_sync": None,
                "validation_status": "unknown",
                "created_at": "2026-02-08T00:00:00",
            },
        )

        class FakeRemoteStore:
            def load_artifact(self, _project, _session, stage):
                if stage == "intent":
                    return "intent from remote"
                if stage == "context":
                    raise RuntimeError("context pull failed")
                raise FileNotFoundError(stage)

        monkeypatch.setattr(
            "idse_orchestrator.artifact_config.ArtifactConfig.get_design_store",
            lambda *_args, **_kwargs: FakeRemoteStore(),
        )

        config_path = Path(".") / ".idseconfig.json"
        config_path.write_text(
            '{"storage_backend":"sqlite","sync_backend":"notion","sqlite":{"db_path":".idse/idse.db"}}'
        )

        result = runner.invoke(
            main,
            [
                "sync",
                "--config",
                str(config_path),
                "pull",
                "--project",
                project,
                "--session",
                session_id,
                "--yes",
            ],
        )
        assert result.exit_code == 0
        assert "✓ intent" in result.output
        assert "Failed: context" in result.output
        assert "- context: context pull failed" in result.output

        pulled = db.load_artifact(project, session_id, "intent")
        assert pulled.content == "intent from remote"


def test_cli_blueprint_promote_allows_and_regenerates(tmp_path):
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        idse_root = Path(".") / ".idse"
        project = "demo"
        (idse_root / "projects" / project / "sessions" / "__blueprint__" / "metadata").mkdir(
            parents=True, exist_ok=True
        )
        (idse_root / "projects" / project / "CURRENT_SESSION").write_text("__blueprint__")

        from idse_orchestrator.artifact_database import ArtifactDatabase

        db = ArtifactDatabase(idse_root=idse_root)
        db.save_artifact(project, "s1", "intent", "SQLite is default storage backend for new projects.")
        db.save_artifact(project, "s2", "spec", "New projects must use SQLite as mandatory backend.")
        db.save_artifact(project, "s1", "feedback", "Implementation feedback confirmed this rule.")
        db.save_artifact(project, "s2", "feedback", "Lessons learned reinforced the invariant.")

        result = runner.invoke(
            main,
            [
                "blueprint",
                "promote",
                "--project",
                project,
                "--claim",
                "SQLite is default storage backend.",
                "--classification",
                "invariant",
                "--source",
                "s1:intent",
                "--source",
                "s2:spec",
                "--min-days",
                "0",
            ],
        )
        assert result.exit_code == 0
        assert "Blueprint Promotion Decision: ALLOW" in result.output
        assert "✅ Blueprint artifacts regenerated" in result.output

        promotions = db.list_blueprint_promotions(project, status="ALLOW")
        assert len(promotions) == 1

        scope = (
            idse_root
            / "projects"
            / project
            / "sessions"
            / "__blueprint__"
            / "metadata"
            / "blueprint.md"
        ).read_text()
        assert "SQLite is default storage backend." in scope


def test_cli_blueprint_declare_creates_declared_claim(tmp_path):
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        idse_root = Path(".") / ".idse"
        project = "demo"
        (idse_root / "projects" / project / "sessions" / "__blueprint__" / "metadata").mkdir(
            parents=True, exist_ok=True
        )

        from idse_orchestrator.artifact_database import ArtifactDatabase

        db = ArtifactDatabase(idse_root=idse_root)
        db.save_artifact(project, "__blueprint__", "intent", "Founding intent")
        db.save_artifact(project, "__blueprint__", "spec", "Founding spec")

        result = runner.invoke(
            main,
            [
                "blueprint",
                "declare",
                "--project",
                project,
                "--claim",
                "SQLite is the authoritative storage backend for project artifacts.",
                "--classification",
                "invariant",
                "--source",
                "__blueprint__:intent",
                "--source",
                "__blueprint__:spec",
            ],
        )
        assert result.exit_code == 0
        assert "Declared claim" in result.output

        claims = db.get_blueprint_claims(project)
        assert len(claims) == 1
        assert claims[0]["origin"] == "declared"
        assert claims[0]["promotion_record_id"] is None


def test_cli_blueprint_reinforce_records_event(tmp_path):
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        idse_root = Path(".") / ".idse"
        project = "demo"
        (idse_root / "projects" / project / "sessions" / "__blueprint__" / "metadata").mkdir(
            parents=True, exist_ok=True
        )

        from idse_orchestrator.artifact_database import ArtifactDatabase

        db = ArtifactDatabase(idse_root=idse_root)
        db.save_artifact(project, "session-1", "feedback", "Reinforcement evidence")
        candidate_id = db.save_promotion_candidate(
            project,
            claim_text="SQLite is authoritative.",
            classification="invariant",
            evidence_hash="seed-hash",
            failed_tests=[],
            evidence={},
            source_artifact_ids=[],
        )
        promotion_record_id = db.save_promotion_record(
            project,
            candidate_id=candidate_id,
            status="ALLOW",
            promoted_claim="SQLite is authoritative.",
            evidence_hash="seed-hash",
        )
        claim_id = db.save_blueprint_claim(
            project,
            claim_text="SQLite is authoritative.",
            classification="invariant",
            promotion_record_id=promotion_record_id,
        )

        result = runner.invoke(
            main,
            [
                "blueprint",
                "reinforce",
                "--project",
                project,
                "--claim-id",
                str(claim_id),
                "--source",
                "session-1:feedback",
            ],
        )
        assert result.exit_code == 0
        assert "Reinforced claim" in result.output

        events = db.get_lifecycle_events(project, claim_id=claim_id)
        assert events[0]["reason"] == "Reinforced by session-1:feedback"


def test_cli_blueprint_extract_candidates(tmp_path):
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        idse_root = Path(".") / ".idse"
        project = "demo"
        (idse_root / "projects" / project).mkdir(parents=True, exist_ok=True)

        from idse_orchestrator.artifact_database import ArtifactDatabase

        db = ArtifactDatabase(idse_root=idse_root)
        db.save_artifact(project, "s1", "spec", "SQLite is the default storage backend for project artifacts.")
        db.save_artifact(project, "s2", "intent", "SQLite is default storage backend for all project artifacts.")
        db.save_artifact(project, "s1", "feedback", "Constraint reinforced during implementation.")
        db.save_artifact(project, "s2", "feedback", "Constraint reinforced by validation.")

        result = runner.invoke(
            main,
            [
                "blueprint",
                "extract-candidates",
                "--project",
                project,
                "--min-sources",
                "2",
                "--min-sessions",
                "2",
                "--min-stages",
                "2",
                "--limit",
                "5",
                "--evaluate",
                "--min-days",
                "0",
            ],
        )
        assert result.exit_code == 0
        assert "Extracted" in result.output
        assert "authoritative storage backend" in result.output
        assert "Gate: ALLOW" in result.output


def test_cli_blueprint_verify_accepts_mismatch(tmp_path):
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        idse_root = Path(".") / ".idse"
        project = "demo"
        (idse_root / "projects" / project / "sessions" / "__blueprint__" / "metadata").mkdir(
            parents=True, exist_ok=True
        )
        (idse_root / "projects" / project / "CURRENT_SESSION").write_text("__blueprint__")

        from idse_orchestrator.artifact_database import ArtifactDatabase
        from idse_orchestrator.file_view_generator import FileViewGenerator

        db = ArtifactDatabase(idse_root=idse_root)
        db.ensure_session(project, "__blueprint__", is_blueprint=True, session_type="blueprint", status="draft")
        generator = FileViewGenerator(idse_root=idse_root)
        scope = generator.ensure_blueprint_scope(project)
        db.save_blueprint_hash(project, "expected")
        scope.write_text(scope.read_text() + "\nmanual edit\n")

        fail = runner.invoke(main, ["blueprint", "verify", "--project", project])
        assert fail.exit_code == 1

        ok = runner.invoke(main, ["blueprint", "verify", "--project", project, "--accept"])
        assert ok.exit_code == 0
        assert "Accepted current blueprint content" in ok.output


def test_cli_blueprint_demote_and_claims(tmp_path):
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        idse_root = Path(".") / ".idse"
        project = "demo"
        (idse_root / "projects" / project / "sessions" / "__blueprint__" / "metadata").mkdir(
            parents=True, exist_ok=True
        )
        (idse_root / "projects" / project / "CURRENT_SESSION").write_text("__blueprint__")

        from idse_orchestrator.artifact_database import ArtifactDatabase
        from idse_orchestrator.file_view_generator import FileViewGenerator

        db = ArtifactDatabase(idse_root=idse_root)
        db.ensure_session(project, "__blueprint__", is_blueprint=True, session_type="blueprint", status="draft")
        candidate_id = db.save_promotion_candidate(
            project,
            claim_text="SQLite is authoritative.",
            classification="invariant",
            evidence_hash="seed-hash",
            failed_tests=[],
            evidence={},
            source_artifact_ids=[],
        )
        promotion_record_id = db.save_promotion_record(
            project,
            candidate_id=candidate_id,
            status="ALLOW",
            promoted_claim="SQLite is authoritative.",
            evidence_hash="seed-hash",
        )
        claim_id = db.save_blueprint_claim(
            project,
            claim_text="SQLite is authoritative.",
            classification="invariant",
            promotion_record_id=promotion_record_id,
        )
        FileViewGenerator(idse_root=idse_root).apply_allowed_promotions_to_blueprint(project)

        claims_out = runner.invoke(main, ["blueprint", "claims", "--project", project])
        assert claims_out.exit_code == 0
        assert "SQLite is authoritative." in claims_out.output

        demote = runner.invoke(
            main,
            [
                "blueprint",
                "demote",
                "--project",
                project,
                "--claim-id",
                str(claim_id),
                "--reason",
                "test reason",
            ],
        )
        assert demote.exit_code == 0
        assert "Demoted claim" in demote.output


def test_cli_compile_agent_spec_passes_backend_override(tmp_path, monkeypatch):
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        captured = {}

        def fake_compile_agent_spec(**kwargs):
            captured.update(kwargs)
            return "id: demo\nname: Demo\n"

        monkeypatch.setattr(
            "idse_orchestrator.compiler.compile_agent_spec",
            fake_compile_agent_spec,
        )

        result = runner.invoke(
            main,
            ["--backend", "sqlite", "compile", "agent-spec", "--session", "s1", "--dry-run"],
        )

        assert result.exit_code == 0
        assert captured["backend"] == "sqlite"
