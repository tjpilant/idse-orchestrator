from hashlib import sha256
from pathlib import Path

import sqlite3

from idse_orchestrator.artifact_database import ArtifactDatabase


def test_artifact_database_schema_created(tmp_path: Path) -> None:
    idse_root = tmp_path / ".idse"
    db = ArtifactDatabase(idse_root=idse_root)

    conn = sqlite3.connect(db.db_path)
    try:
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table';"
        ).fetchall()
    finally:
        conn.close()

    table_names = {row[0] for row in rows}
    for required in {
        "projects",
        "sessions",
        "artifacts",
        "artifact_dependencies",
        "sync_metadata",
        "project_state",
        "agents",
        "agent_stages",
        "collaborators",
        "session_tags",
    }:
        assert required in table_names


def test_artifact_database_crud(tmp_path: Path) -> None:
    idse_root = tmp_path / ".idse"
    db = ArtifactDatabase(idse_root=idse_root)

    project = "demo"
    session = "session-1"
    stage = "intent"
    content = "hello world"

    record = db.save_artifact(project, session, stage, content)
    assert record.content == content
    assert record.idse_id == f"{project}::{session}::{stage}"
    assert record.content_hash == sha256(content.encode("utf-8")).hexdigest()

    fetched = db.load_artifact(project, session, stage)
    assert fetched.content == content
    assert fetched.idse_id == f"{project}::{session}::{stage}"

    sessions = db.list_sessions(project)
    assert session in sessions

    state = {"project_name": project, "session_id": session, "stages": {"intent": "completed"}}
    db.save_state(project, state)
    assert db.load_state(project) == state


def test_save_session_state_does_not_reset_session_status(tmp_path: Path) -> None:
    idse_root = tmp_path / ".idse"
    db = ArtifactDatabase(idse_root=idse_root)

    project = "demo"
    session = "session-1"
    db.ensure_session(project, session, status="complete")

    session_state = {
        "project_name": project,
        "session_id": session,
        "is_blueprint": False,
        "stages": {"intent": "completed"},
        "last_sync": None,
        "validation_status": "passing",
        "created_at": "2026-02-07T00:00:00",
    }
    db.save_session_state(project, session, session_state)

    metadata = db.list_session_metadata(project)
    row = next(item for item in metadata if item["session_id"] == session)
    assert row["status"] == "complete"


def test_find_by_idse_id_and_dependencies_and_sync_metadata(tmp_path: Path) -> None:
    idse_root = tmp_path / ".idse"
    db = ArtifactDatabase(idse_root=idse_root)

    project = "demo"
    a = db.save_artifact(project, "s1", "intent", "artifact a")
    b = db.save_artifact(project, "s1", "spec", "artifact b")

    found = db.find_by_idse_id(a.idse_id)
    assert found is not None
    assert found.content == "artifact a"

    with db._connect() as conn:
        a_id = conn.execute(
            """
            SELECT a.id
            FROM artifacts a
            JOIN sessions s ON a.session_id = s.id
            JOIN projects p ON a.project_id = p.id
            WHERE p.name = ? AND s.session_id = ? AND a.stage = ?;
            """,
            (project, "s1", "intent"),
        ).fetchone()["id"]
        b_id = conn.execute(
            """
            SELECT a.id
            FROM artifacts a
            JOIN sessions s ON a.session_id = s.id
            JOIN projects p ON a.project_id = p.id
            WHERE p.name = ? AND s.session_id = ? AND a.stage = ?;
            """,
            (project, "s1", "spec"),
        ).fetchone()["id"]

    db.save_dependency(a_id, b_id, "upstream")
    upstream = db.get_dependencies(a_id, direction="upstream")
    assert len(upstream) == 1
    assert upstream[0].stage == "spec"

    downstream = db.get_dependencies(b_id, direction="downstream")
    assert len(downstream) == 1
    assert downstream[0].stage == "intent"

    db.save_sync_metadata(a_id, "notion", last_push_hash="abc123", remote_id="remote-1")
    meta = db.get_sync_metadata(a_id, "notion")
    assert meta["last_push_hash"] == "abc123"
    assert meta["remote_id"] == "remote-1"

    db.save_sync_metadata(a_id, "notion", last_pull_hash="def456")
    meta2 = db.get_sync_metadata(a_id, "notion")
    assert meta2["last_push_hash"] == "abc123"
    assert meta2["last_pull_hash"] == "def456"
    assert meta2["remote_id"] == "remote-1"
    assert db.find_artifact_id_by_remote_id("notion", "remote-1") == a_id


def test_replace_dependencies_replaces_existing_links(tmp_path: Path) -> None:
    idse_root = tmp_path / ".idse"
    db = ArtifactDatabase(idse_root=idse_root)

    project = "demo"
    root = db.save_artifact(project, "s1", "tasks", "root")
    a = db.save_artifact(project, "s1", "intent", "a")
    b = db.save_artifact(project, "s1", "context", "b")

    root_id = db.get_artifact_id(root.project, root.session_id, root.stage)
    a_id = db.get_artifact_id(a.project, a.session_id, a.stage)
    b_id = db.get_artifact_id(b.project, b.session_id, b.stage)
    assert root_id is not None
    assert a_id is not None
    assert b_id is not None

    db.replace_dependencies(root_id, [a_id], dependency_type="upstream")
    first = db.get_dependencies(root_id, direction="upstream")
    assert [rec.stage for rec in first] == ["intent"]

    db.replace_dependencies(root_id, [b_id], dependency_type="upstream")
    second = db.get_dependencies(root_id, direction="upstream")
    assert [rec.stage for rec in second] == ["context"]


def test_backfill_idse_id_for_legacy_rows(tmp_path: Path) -> None:
    idse_root = tmp_path / ".idse"
    idse_root.mkdir(parents=True, exist_ok=True)
    db_path = idse_root / "idse.db"

    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            """
            CREATE TABLE projects (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                stack TEXT,
                owner TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                current_session_id TEXT
            );
            """
        )
        conn.execute(
            """
            CREATE TABLE sessions (
                id INTEGER PRIMARY KEY,
                project_id INTEGER NOT NULL,
                session_id TEXT NOT NULL,
                name TEXT NOT NULL,
                session_type TEXT NOT NULL,
                description TEXT,
                is_blueprint INTEGER NOT NULL DEFAULT 0,
                parent_session TEXT,
                owner TEXT,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(project_id, session_id)
            );
            """
        )
        # Legacy artifacts table intentionally has no idse_id column.
        conn.execute(
            """
            CREATE TABLE artifacts (
                id INTEGER PRIMARY KEY,
                project_id INTEGER NOT NULL,
                session_id INTEGER NOT NULL,
                stage TEXT NOT NULL,
                content TEXT NOT NULL,
                content_hash TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(session_id, stage)
            );
            """
        )
        conn.execute(
            """
            INSERT INTO projects (id, name, stack, owner, created_at, updated_at, current_session_id)
            VALUES (1, 'demo', 'python', 'system', '2026-02-07T00:00:00', '2026-02-07T00:00:00', NULL);
            """
        )
        conn.execute(
            """
            INSERT INTO sessions (id, project_id, session_id, name, session_type, is_blueprint, status, created_at, updated_at)
            VALUES (1, 1, 's1', 's1', 'feature', 0, 'draft', '2026-02-07T00:00:00', '2026-02-07T00:00:00');
            """
        )
        conn.execute(
            """
            INSERT INTO artifacts (id, project_id, session_id, stage, content, content_hash, created_at, updated_at)
            VALUES (1, 1, 1, 'intent', 'hello', 'x', '2026-02-07T00:00:00', '2026-02-07T00:00:00');
            """
        )
        conn.commit()
    finally:
        conn.close()

    db = ArtifactDatabase(db_path=db_path)
    rec = db.load_artifact("demo", "s1", "intent")
    assert rec.idse_id == "demo::s1::intent"


def test_blueprint_claims_migration_defaults_origin_to_converged(tmp_path: Path) -> None:
    idse_root = tmp_path / ".idse"
    idse_root.mkdir(parents=True, exist_ok=True)
    db_path = idse_root / "idse.db"

    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            """
            CREATE TABLE projects (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                stack TEXT,
                owner TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                current_session_id TEXT
            );
            """
        )
        conn.execute(
            """
            CREATE TABLE promotion_records (
                id INTEGER PRIMARY KEY,
                project_id INTEGER NOT NULL,
                candidate_id INTEGER NOT NULL,
                status TEXT NOT NULL,
                promoted_claim TEXT,
                evidence_hash TEXT,
                created_at TEXT NOT NULL,
                promoted_at TEXT
            );
            """
        )
        conn.execute(
            """
            CREATE TABLE blueprint_claims (
                claim_id INTEGER PRIMARY KEY,
                project_id INTEGER NOT NULL,
                claim_text TEXT NOT NULL,
                classification TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'active',
                supersedes_claim_id INTEGER,
                promotion_record_id INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(project_id, claim_text)
            );
            """
        )
        conn.execute(
            """
            INSERT INTO projects (id, name, stack, owner, created_at, updated_at, current_session_id)
            VALUES (1, 'demo', 'python', 'system', '2026-02-07T00:00:00', '2026-02-07T00:00:00', NULL);
            """
        )
        conn.execute(
            """
            INSERT INTO promotion_records (
                id, project_id, candidate_id, status, promoted_claim, evidence_hash, created_at, promoted_at
            )
            VALUES (
                1, 1, 1, 'ALLOW', 'Legacy converged claim', 'legacy-hash',
                '2026-02-07T00:00:00', '2026-02-07T00:00:00'
            );
            """
        )
        conn.execute(
            """
            INSERT INTO blueprint_claims (
                claim_id, project_id, claim_text, classification, status, supersedes_claim_id,
                promotion_record_id, created_at, updated_at
            )
            VALUES (
                1, 1, 'Legacy converged claim', 'invariant', 'active', NULL, 1,
                '2026-02-07T00:00:00', '2026-02-07T00:00:00'
            );
            """
        )
        conn.commit()
    finally:
        conn.close()

    db = ArtifactDatabase(db_path=db_path)
    claims = db.get_blueprint_claims("demo")
    assert len(claims) == 1
    assert claims[0]["origin"] == "converged"
