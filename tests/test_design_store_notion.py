from idse_orchestrator.design_store_notion import NotionDesignStore, NotionSchemaMap
from idse_orchestrator.artifact_database import ArtifactDatabase, hash_content


def test_notion_property_helpers():
    store = NotionDesignStore(database_id="db123")

    assert store._property_filter("session", "demo-session") == {
        "property": "Session",
        "rich_text": {"equals": "demo-session"},
    }

    assert store._property_value("stage", "intent") == {
        "select": {"name": "intent"}
    }

    page = {
        "properties": {
            "Content": {
                "rich_text": [
                    {"plain_text": "hello"},
                    {"plain_text": " world"},
                ]
            }
        }
    }
    # Default config uses page_body content, so property text is ignored
    assert store._extract_property_text(page, "content") == ""


def test_notion_text_type_normalizes():
    store = NotionDesignStore(
        database_id="db123",
        properties={
            "project": {"name": "Project", "type": "text"},
            "session": {"name": "Session", "type": "text"},
            "stage": {"name": "Stage", "type": "select"},
            "content": {"name": "page_body", "type": "page_body"},
        },
    )

    assert store.properties["project"]["type"] == "rich_text"
    assert store.properties["session"]["type"] == "rich_text"
    assert store.properties["content"]["type"] == "page_body"


def test_flatten_property_values():
    from idse_orchestrator.design_store_notion import _flatten_property_values

    properties = {
        "Title": {"title": [{"plain_text": "Intent"}]},
        "Project": {"rich_text": [{"plain_text": "demo"}]},
        "Stage": {"select": {"name": "intent"}},
        "Status": {"status": {"name": "in_progress"}},
    }

    assert _flatten_property_values(properties) == {
        "Title": "Intent",
        "Project": "demo",
        "Stage": "intent",
        "Status": "in_progress",
    }


def test_notion_schema_map_computed_fields():
    props = {
        "title": {"name": "Title", "type": "title"},
        "idse_id": {"name": "IDSE_ID", "type": "rich_text"},
        "project": {"name": "Project", "type": "rich_text"},
        "session": {"name": "Session", "type": "rich_text"},
        "stage": {"name": "Stage", "type": "select"},
        "status": {"name": "Status", "type": "status"},
        "layer": {"name": "Layer", "type": "select"},
        "run_scope": {"name": "Run Scope", "type": "select"},
        "version": {"name": "Version", "type": "rich_text"},
        "feature_capability": {"name": "Feature / Capability", "type": "rich_text"},
        "content": {"name": "body", "type": "page_body"},
    }
    schema_map = NotionSchemaMap(props)
    result = schema_map.build_projection(
        project="demo",
        session_id="feature-v2",
        stage="implementation",
        content="hello",
        include_idse_id=True,
        content_type="page_body",
        write_mode="create",
        session_status="in_progress",
        tags=["platform", "feature"],
        version="v2",
        feature_capability="Notion sync",
    )

    fields = result["fields"]
    assert fields["title"] == "Test Plan – feature-v2"
    assert fields["idse_id"] == "demo::feature-v2::implementation"
    assert fields["status"] == "In Review"
    assert fields["layer"] == "Platform"
    assert fields["run_scope"] == "Feature"
    assert fields["version"] == "v2"
    assert fields["feature_capability"] == "Notion sync"
    assert result["content_payload"] == "hello"


def test_notion_status_property_helpers():
    store = NotionDesignStore(database_id="db123")
    assert store._property_filter("status", "in_progress") == {
        "property": "Status",
        "status": {"equals": "in_progress"},
    }
    assert store._property_value("status", "in_progress") == {
        "status": {"name": "in_progress"}
    }


def test_notion_schema_map_status_mapping():
    store = NotionDesignStore(database_id="db123")
    result = store.schema_map.build_projection(
        project="demo",
        session_id="s1",
        stage="intent",
        content="hello",
        include_idse_id=True,
        content_type="page_body",
        write_mode="create",
        session_status="archived",
    )
    assert result["fields"]["status"] == "Superseded"


def test_notion_schema_map_excludes_create_only_fields_on_update():
    store = NotionDesignStore(database_id="db123")
    result = store.schema_map.build_projection(
        project="demo",
        session_id="feature-v2",
        stage="plan",
        content="hello",
        include_idse_id=True,
        content_type="page_body",
        write_mode="update",
    )
    assert "title" not in result["fields"]
    assert result["fields"]["session"] == "feature-v2"


def test_resolve_page_id_uses_sync_metadata_cache(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    from idse_orchestrator.artifact_database import ArtifactDatabase

    idse_root = tmp_path / ".idse"
    db = ArtifactDatabase(idse_root=idse_root)
    db.save_artifact("demo", "s1", "intent", "hello")
    artifact_id = db.get_artifact_id("demo", "s1", "intent")
    assert artifact_id is not None
    db.save_sync_metadata(artifact_id, "notion", remote_id="page-cache-1")

    store = NotionDesignStore(database_id="db123")
    monkeypatch.setattr(
        store,
        "_query_database",
        lambda filters: (_ for _ in ()).throw(RuntimeError("should not query")),
    )
    assert store._resolve_page_id("demo", "s1", "intent") == "page-cache-1"


def test_resolve_page_id_fallback_queries_and_caches(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    from idse_orchestrator.artifact_database import ArtifactDatabase

    idse_root = tmp_path / ".idse"
    db = ArtifactDatabase(idse_root=idse_root)
    db.save_artifact("demo", "s1", "intent", "hello")
    artifact_id = db.get_artifact_id("demo", "s1", "intent")
    assert artifact_id is not None

    store = NotionDesignStore(database_id="db123")
    monkeypatch.setattr(store, "_query_database", lambda filters: [{"id": "page-fallback-1"}])

    page_id = store._resolve_page_id("demo", "s1", "intent")
    assert page_id == "page-fallback-1"

    meta = db.get_sync_metadata(artifact_id, "notion")
    assert meta["remote_id"] == "page-fallback-1"


def test_save_artifact_skips_when_hash_unchanged(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    idse_root = tmp_path / ".idse"
    db = ArtifactDatabase(idse_root=idse_root)
    rec = db.save_artifact("demo", "s1", "intent", "same-content")
    artifact_id = db.get_artifact_id("demo", "s1", "intent")
    assert artifact_id is not None
    db.save_sync_metadata(
        artifact_id,
        "notion",
        last_push_hash=hash_content("same-content"),
        remote_id="page-1",
    )

    store = NotionDesignStore(database_id="db123")
    monkeypatch.setattr(
        store,
        "_call_tool",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("should not call MCP")),
    )
    store.save_artifact("demo", "s1", "intent", "same-content")
    assert store.last_write_skipped is True

    meta = db.get_sync_metadata(artifact_id, "notion")
    assert meta["last_push_hash"] == hash_content("same-content")
    assert meta["remote_id"] == "page-1"


def test_save_artifact_does_not_skip_when_remote_id_missing(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    idse_root = tmp_path / ".idse"
    db = ArtifactDatabase(idse_root=idse_root)
    db.save_artifact("demo", "s1", "intent", "same-content")
    artifact_id = db.get_artifact_id("demo", "s1", "intent")
    assert artifact_id is not None
    db.save_sync_metadata(
        artifact_id,
        "notion",
        last_push_hash=hash_content("same-content"),
        remote_id=None,
    )

    store = NotionDesignStore(database_id="db123")
    monkeypatch.setattr(store, "_resolve_page_id", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(store, "_call_tool", lambda *_args, **_kwargs: {"id": "page-created-2"})
    store.tool_names["create_page"] = "notion-create-pages"

    store.save_artifact("demo", "s1", "intent", "same-content")
    assert store.last_write_skipped is False

    meta = db.get_sync_metadata(artifact_id, "notion")
    assert meta["remote_id"] == "page-created-2"


def test_save_artifact_updates_push_metadata(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    idse_root = tmp_path / ".idse"
    db = ArtifactDatabase(idse_root=idse_root)
    db.save_artifact("demo", "s1", "intent", "old-content")
    artifact_id = db.get_artifact_id("demo", "s1", "intent")
    assert artifact_id is not None

    store = NotionDesignStore(database_id="db123")
    monkeypatch.setattr(store, "_resolve_page_id", lambda *_args, **_kwargs: None)

    calls = []

    def fake_call(tool_name, payload):
        calls.append((tool_name, payload))
        return {"id": "page-created-1"}

    monkeypatch.setattr(store, "_call_tool", fake_call)
    store.tool_names["create_page"] = "notion-create-pages"
    store.save_artifact("demo", "s1", "intent", "new-content")
    assert store.last_write_skipped is False
    assert calls

    meta = db.get_sync_metadata(artifact_id, "notion")
    assert meta["last_push_hash"] == hash_content("new-content")
    assert meta["remote_id"] == "page-created-1"


def test_extract_page_id_handles_nested_results():
    from idse_orchestrator.design_store_notion import _extract_page_id

    payload = {"results": [{"id": "page-nested-1"}]}
    assert _extract_page_id(payload) == "page-nested-1"


def test_extract_page_id_from_notion_url():
    from idse_orchestrator.design_store_notion import _extract_page_id

    payload = {
        "results": [
            {"url": "https://www.notion.so/301ffccab9d681db834fd3a1132b4a7a"}
        ]
    }
    assert _extract_page_id(payload) == "301ffccab9d681db834fd3a1132b4a7a"


def test_load_artifact_upserts_and_tracks_pull_metadata(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    idse_root = tmp_path / ".idse"
    db = ArtifactDatabase(idse_root=idse_root)

    store = NotionDesignStore(database_id="db123")
    monkeypatch.setattr(store, "_resolve_page_id", lambda *_args, **_kwargs: "page-xyz")
    monkeypatch.setattr(
        store,
        "_call_tool",
        lambda tool, payload: {
            "blocks": [
                {
                    "type": "paragraph",
                    "paragraph": {"rich_text": [{"plain_text": "pulled content"}]},
                }
            ]
        },
    )

    content = store.load_artifact("demo", "s2", "spec")
    assert content == "pulled content"

    rec = db.load_artifact("demo", "s2", "spec")
    assert rec.content == "pulled content"
    artifact_id = db.get_artifact_id("demo", "s2", "spec")
    assert artifact_id is not None
    meta = db.get_sync_metadata(artifact_id, "notion")
    assert meta["last_pull_hash"] == hash_content("pulled content")
    assert meta["remote_id"] == "page-xyz"


def test_load_artifact_uses_notion_fetch_id_payload(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    ArtifactDatabase(idse_root=tmp_path / ".idse")

    store = NotionDesignStore(database_id="db123")
    monkeypatch.setattr(store, "_resolve_page_id", lambda *_args, **_kwargs: "page-xyz")

    seen = {}

    def fake_call(_tool, payload):
        seen.update(payload)
        return {"blocks": []}

    monkeypatch.setattr(store, "_call_tool", fake_call)
    store.load_artifact("demo", "s1", "intent")
    assert seen.get("id") == "page-xyz"


def test_load_artifact_maps_upstream_relations_to_dependencies(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    idse_root = tmp_path / ".idse"
    db = ArtifactDatabase(idse_root=idse_root)

    dep = db.save_artifact("demo", "s1", "intent", "dep")
    dep_artifact_id = db.get_artifact_id(dep.project, dep.session_id, dep.stage)
    assert dep_artifact_id is not None
    db.save_sync_metadata(dep_artifact_id, "notion", remote_id="page-dep-1")

    store = NotionDesignStore(database_id="db123")
    monkeypatch.setattr(store, "_resolve_page_id", lambda *_args, **_kwargs: "page-target-1")
    monkeypatch.setattr(
        store,
        "_call_tool",
        lambda _tool, _payload: {
            "properties": {
                "Upstream Artifact": {"relation": [{"id": "page-dep-1"}]}
            },
            "blocks": [
                {
                    "type": "paragraph",
                    "paragraph": {"rich_text": [{"plain_text": "pulled target"}]},
                }
            ],
        },
    )

    content = store.load_artifact("demo", "s2", "spec")
    assert content == "pulled target"

    target_artifact_id = db.get_artifact_id("demo", "s2", "spec")
    assert target_artifact_id is not None
    upstream = db.get_dependencies(target_artifact_id, direction="upstream")
    assert len(upstream) == 1
    assert upstream[0].idse_id == dep.idse_id


def test_save_artifact_pushes_upstream_dependency_relations(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    idse_root = tmp_path / ".idse"
    db = ArtifactDatabase(idse_root=idse_root)

    target = db.save_artifact("demo", "s2", "spec", "target old")
    dep = db.save_artifact("demo", "s1", "intent", "dep")
    target_artifact_id = db.get_artifact_id(target.project, target.session_id, target.stage)
    dep_artifact_id = db.get_artifact_id(dep.project, dep.session_id, dep.stage)
    assert target_artifact_id is not None
    assert dep_artifact_id is not None
    db.save_dependency(target_artifact_id, dep_artifact_id, "upstream")
    db.save_sync_metadata(dep_artifact_id, "notion", remote_id="page-dep-1")

    store = NotionDesignStore(database_id="db123")
    monkeypatch.setattr(store, "_resolve_page_id", lambda *_args, **_kwargs: "page-target-1")

    calls = []

    def fake_call(tool_name, payload):
        calls.append((tool_name, payload))
        return {"ok": True}

    monkeypatch.setattr(store, "_call_tool", fake_call)

    store.save_artifact("demo", "s2", "spec", "target new")

    relation_updates = [
        payload
        for tool_name, payload in calls
        if tool_name == store.tool_names["update_page"]
        and payload.get("data", {}).get("command") == "update_properties"
        and "Upstream Artifact" in payload.get("data", {}).get("properties", {})
    ]
    assert relation_updates, "expected relation update payload"
    assert relation_updates[-1]["data"]["properties"]["Upstream Artifact"] == ["page-dep-1"]
