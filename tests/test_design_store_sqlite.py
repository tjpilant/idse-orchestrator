from pathlib import Path

from idse_orchestrator.design_store_sqlite import DesignStoreSQLite


def test_design_store_sqlite_crud(tmp_path: Path) -> None:
    idse_root = tmp_path / ".idse"
    store = DesignStoreSQLite(idse_root=idse_root)

    project = "demo"
    session = "s1"

    store.save_artifact(project, session, "intent", "hello")
    assert store.load_artifact(project, session, "intent") == "hello"

    sessions = store.list_sessions(project)
    assert session in sessions

    state = {"project_name": project, "session_id": session}
    store.save_state(project, state)
    assert store.load_state(project) == state
