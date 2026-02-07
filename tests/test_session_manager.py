from pathlib import Path

from idse_orchestrator.session_manager import SessionManager


def test_legacy_session_uses_valid_status_for_statistics(tmp_path: Path):
    project_path = tmp_path / "project"
    legacy_session = project_path / "sessions" / "legacy-session" / "metadata"
    legacy_session.mkdir(parents=True, exist_ok=True)
    (legacy_session / ".owner").write_text("Created: 2026-02-07T00:00:00\nClient ID: system\n")

    manager = SessionManager(project_path)
    sessions = manager.list_sessions(include_legacy=True)

    assert len(sessions) == 1
    assert sessions[0].status == "draft"
    assert "legacy" in sessions[0].tags

    stats = manager.get_statistics()
    assert stats["total_sessions"] == 1
    assert stats["by_status"]["draft"] == 1
