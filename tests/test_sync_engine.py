from idse_orchestrator.design_store import DesignStoreFilesystem
from idse_orchestrator.sync_engine import SyncEngine
from idse_orchestrator.stage_state_model import StageStateModel


def test_push_saves_artifacts(tmp_path):
    idse_root = tmp_path / ".idse"
    project_path = idse_root / "projects" / "test-project"
    project_path.mkdir(parents=True)

    store = DesignStoreFilesystem(idse_root)
    tracker = StageStateModel(project_path)
    tracker.init_state("test-project", "__blueprint__")

    engine = SyncEngine(store, tracker)
    result = engine.push("test-project", "__blueprint__", {"intent": "# Test intent"})

    assert "intent" in result["synced_stages"]
    assert store.load_artifact("test-project", "__blueprint__", "intent") == "# Test intent"


def test_push_updates_last_sync(tmp_path):
    idse_root = tmp_path / ".idse"
    project_path = idse_root / "projects" / "test-project"
    project_path.mkdir(parents=True)

    store = DesignStoreFilesystem(idse_root)
    tracker = StageStateModel(project_path)
    tracker.init_state("test-project", "__blueprint__")

    engine = SyncEngine(store, tracker)
    engine.push("test-project", "__blueprint__", {"intent": "# Test"})

    state = tracker.get_status()
    assert state["last_sync"] is not None


def test_pull_reads_artifacts(tmp_path):
    idse_root = tmp_path / ".idse"
    project_path = idse_root / "projects" / "test-project"
    project_path.mkdir(parents=True)

    store = DesignStoreFilesystem(idse_root)
    store.save_artifact("test-project", "__blueprint__", "intent", "# Pulled intent")

    tracker = StageStateModel(project_path)
    tracker.init_state("test-project", "__blueprint__")

    engine = SyncEngine(store, tracker)
    artifacts = engine.pull("test-project", "__blueprint__")

    assert artifacts["intent"] == "# Pulled intent"


def test_pull_skips_missing_artifacts(tmp_path):
    idse_root = tmp_path / ".idse"
    project_path = idse_root / "projects" / "test-project"
    project_path.mkdir(parents=True)

    store = DesignStoreFilesystem(idse_root)
    tracker = StageStateModel(project_path)
    tracker.init_state("test-project", "__blueprint__")

    engine = SyncEngine(store, tracker)
    artifacts = engine.pull("test-project", "__blueprint__")

    assert artifacts == {}
