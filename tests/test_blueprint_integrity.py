from pathlib import Path

from idse_orchestrator.artifact_database import ArtifactDatabase, hash_content
from idse_orchestrator.file_view_generator import FileViewGenerator


def _seed_allow_promotion(db: ArtifactDatabase, project: str) -> None:
    db.ensure_session(project, "__blueprint__", is_blueprint=True, session_type="blueprint", status="draft")
    db.save_artifact(project, "s1", "intent", "intent")
    db.save_artifact(project, "s2", "spec", "spec")
    a_id = db.get_artifact_id(project, "s1", "intent")
    b_id = db.get_artifact_id(project, "s2", "spec")
    assert a_id is not None
    assert b_id is not None
    db.save_blueprint_promotion(
        project,
        claim_text="SQLite is the authoritative storage backend for project artifacts.",
        classification="invariant",
        status="ALLOW",
        evidence_hash="hash-allow",
        failed_tests=[],
        evidence={
            "source_sessions": ["s1", "s2"],
            "source_stages": ["intent", "spec"],
            "feedback_artifacts": [],
        },
        source_artifact_ids=[a_id, b_id],
        promoted_at="2026-02-08T00:00:00",
    )


def test_integrity_tables_exist(tmp_path: Path) -> None:
    db = ArtifactDatabase(idse_root=tmp_path / ".idse")
    with db._connect() as conn:
        tables = {row["name"] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table';")}
    assert "blueprint_integrity" in tables
    assert "integrity_events" in tables


def test_save_and_get_blueprint_hash(tmp_path: Path) -> None:
    db = ArtifactDatabase(idse_root=tmp_path / ".idse")
    db.save_blueprint_hash("demo", "abc123")
    assert db.get_blueprint_hash("demo") == "abc123"


def test_get_blueprint_hash_none_when_empty(tmp_path: Path) -> None:
    db = ArtifactDatabase(idse_root=tmp_path / ".idse")
    assert db.get_blueprint_hash("demo") is None


def test_apply_promotions_stores_blueprint_hash(tmp_path: Path) -> None:
    idse_root = tmp_path / ".idse"
    db = ArtifactDatabase(idse_root=idse_root)
    project = "demo"
    _seed_allow_promotion(db, project)

    generator = FileViewGenerator(idse_root=idse_root)
    scope_path = generator.apply_allowed_promotions_to_blueprint(project)
    expected_hash = hash_content(scope_path.read_text())
    assert db.get_blueprint_hash(project) == expected_hash


def test_verify_detects_tampering_and_records_event(tmp_path: Path) -> None:
    idse_root = tmp_path / ".idse"
    db = ArtifactDatabase(idse_root=idse_root)
    project = "demo"
    _seed_allow_promotion(db, project)

    generator = FileViewGenerator(idse_root=idse_root)
    scope_path = generator.apply_allowed_promotions_to_blueprint(project)
    scope_path.write_text(scope_path.read_text() + "\nManual unauthorized edit.\n")

    warning = generator.verify_blueprint_integrity(project)
    assert warning is not None
    assert "Blueprint integrity mismatch detected" in warning

    with db._connect() as conn:
        events = conn.execute("SELECT action FROM integrity_events ORDER BY id DESC;").fetchall()
    assert events
    assert events[0]["action"] == "warn"


def test_verify_returns_none_when_untampered(tmp_path: Path) -> None:
    idse_root = tmp_path / ".idse"
    db = ArtifactDatabase(idse_root=idse_root)
    project = "demo"
    _seed_allow_promotion(db, project)

    generator = FileViewGenerator(idse_root=idse_root)
    generator.apply_allowed_promotions_to_blueprint(project)
    assert generator.verify_blueprint_integrity(project) is None


def test_verify_no_false_positive_without_stored_hash(tmp_path: Path) -> None:
    idse_root = tmp_path / ".idse"
    db = ArtifactDatabase(idse_root=idse_root)
    project = "demo"
    db.ensure_session(project, "__blueprint__", is_blueprint=True, session_type="blueprint", status="draft")

    generator = FileViewGenerator(idse_root=idse_root)
    generator.ensure_blueprint_scope(project)
    assert generator.verify_blueprint_integrity(project) is None


def test_record_integrity_accept_event(tmp_path: Path) -> None:
    db = ArtifactDatabase(idse_root=tmp_path / ".idse")
    db.record_integrity_event("demo", "expected", "actual", action="accept")
    with db._connect() as conn:
        row = conn.execute(
            "SELECT action, expected_hash, actual_hash FROM integrity_events ORDER BY id DESC LIMIT 1;"
        ).fetchone()
    assert row is not None
    assert row["action"] == "accept"
    assert row["expected_hash"] == "expected"
    assert row["actual_hash"] == "actual"
