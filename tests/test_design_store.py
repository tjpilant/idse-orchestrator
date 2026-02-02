from pathlib import Path

from idse_orchestrator.design_store import DesignStoreFilesystem


def test_design_store_filesystem_crud(tmp_path: Path):
    idse_root = tmp_path / ".idse"
    store = DesignStoreFilesystem(idse_root)
    project = "demo"
    session = "s1"

    # Save/load artifact
    store.save_artifact(project, session, "intent", "hello")
    assert store.load_artifact(project, session, "intent") == "hello"

    # List sessions
    sessions = store.list_sessions(project)
    assert session in sessions

    # Save/load state
    state = {"project_name": project, "session_id": session}
    store.save_state(project, state)
    assert store.load_state(project) == state
