from pathlib import Path
import sqlite3

from idse_orchestrator.artifact_database import ArtifactDatabase
from idse_orchestrator.migration import FileToDatabaseMigrator


def test_file_to_db_migration(tmp_path: Path) -> None:
    idse_root = tmp_path / ".idse"
    project = "demo"
    project_path = idse_root / "projects" / project
    session_path = project_path / "sessions" / "__blueprint__"

    (session_path / "intents").mkdir(parents=True, exist_ok=True)
    (session_path / "metadata").mkdir(parents=True, exist_ok=True)

    (session_path / "intents" / "intent.md").write_text("intent content")
    (session_path / "metadata" / "session.json").write_text(
        """
        {
          "session_id": "__blueprint__",
          "name": "Demo Blueprint",
          "session_type": "blueprint",
          "description": "test",
          "is_blueprint": true,
          "parent_session": null,
          "related_sessions": [],
          "owner": "system",
          "collaborators": [{"name": "Alice", "role": "owner", "joined_at": "2026-02-04T00:00:00"}],
          "tags": ["core"],
          "status": "draft",
          "created_at": "2026-02-04T00:00:00",
          "updated_at": "2026-02-04T00:00:00"
        }
        """
    )

    (project_path / "session_state.json").write_text(
        '{"project_name": "demo", "session_id": "__blueprint__", "stages": {"intent": "completed"}}'
    )
    (project_path / "agent_registry.json").write_text(
        '{"agents": [{"id": "gpt-codex", "role": "implementer", "mode": "implementation", "stages": ["implementation"]}]}'
    )

    migrator = FileToDatabaseMigrator(idse_root=idse_root)
    results = migrator.migrate_project(project_name=project)
    assert "__blueprint__" in results

    db = ArtifactDatabase(idse_root=idse_root)
    record = db.load_artifact(project, "__blueprint__", "intent")
    assert record.content == "intent content"

    state = db.load_session_state(project, "__blueprint__")
    assert state["project_name"] == "demo"

    conn = sqlite3.connect(db.db_path)
    try:
        row = conn.execute(
            "SELECT agent_id, role, mode FROM agents WHERE agent_id = 'gpt-codex';"
        ).fetchone()
    finally:
        conn.close()
    assert row is not None
