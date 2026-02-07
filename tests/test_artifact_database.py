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
    assert record.content_hash == sha256(content.encode("utf-8")).hexdigest()

    fetched = db.load_artifact(project, session, stage)
    assert fetched.content == content

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
