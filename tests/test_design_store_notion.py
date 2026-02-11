from idse_orchestrator.design_store_notion import (
    NotionDesignStore,
    NotionSchemaMap,
    _normalize_view_url,
)
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


def test_normalize_view_url_uses_dashed_uuid():
    assert _normalize_view_url("5041d74b1dcb4a53a426668c72dacf3e") == (
        "view://5041d74b-1dcb-4a53-a426-668c72dacf3e"
    )
    assert _normalize_view_url("view://5041d74b1dcb4a53a426668c72dacf3e") == (
        "view://5041d74b-1dcb-4a53-a426-668c72dacf3e"
    )


def test_notion_text_type_normalizes():
    store = NotionDesignStore(
        database_id="db123",
        properties={
            "session": {"name": "Session", "type": "text"},
            "stage": {"name": "Stage", "type": "select"},
            "content": {"name": "page_body", "type": "page_body"},
        },
    )

    assert store.properties["session"]["type"] == "rich_text"
    assert store.properties["content"]["type"] == "page_body"


def test_flatten_property_values():
    from idse_orchestrator.design_store_notion import _flatten_property_values

    properties = {
        "Title": {"title": [{"plain_text": "Intent"}]},
        "Stage": {"select": {"name": "intent"}},
        "Status": {"status": {"name": "in_progress"}},
    }

    assert _flatten_property_values(properties) == {
        "Title": "Intent",
        "Stage": "intent",
        "Status": "in_progress",
    }


def test_notion_schema_map_computed_fields():
    props = {
        "title": {"name": "Title", "type": "title"},
        "idse_id": {"name": "IDSE_ID", "type": "rich_text"},
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
    assert fields["title"] == "Implementation – feature-v2"
    assert "project" not in fields
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


def test_title_uses_stage_session_format():
    schema_map = NotionSchemaMap(NotionDesignStore.DEFAULT_PROPERTIES)
    result = schema_map.build_projection(
        project="idse-orchestrator",
        session_id="my-session",
        stage="intent",
        content="# Intent",
        include_idse_id=False,
        content_type="page_body",
    )
    assert result["fields"]["title"] == "Intent – my-session"
    assert "project" not in result["fields"]


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


def test_resolve_page_id_prefers_idse_id_query(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    idse_root = tmp_path / ".idse"
    db = ArtifactDatabase(idse_root=idse_root)
    db.save_artifact("demo", "s1", "intent", "hello")

    store = NotionDesignStore(database_id="db123")
    calls = []

    def fake_query(filters):
        calls.append(filters)
        return [{"id": "page-by-idse"}]

    monkeypatch.setattr(store, "_query_database", fake_query)
    page_id = store._resolve_page_id("demo", "s1", "intent")
    assert page_id == "page-by-idse"
    assert calls
    assert calls[0][0]["property"] == "IDSE_ID"


def test_resolve_page_id_skips_archived_pages(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    idse_root = tmp_path / ".idse"
    db = ArtifactDatabase(idse_root=idse_root)
    db.save_artifact("demo", "s1", "intent", "hello")

    store = NotionDesignStore(database_id="db123")
    monkeypatch.setattr(
        store,
        "_query_database",
        lambda _filters: [
            {"id": "page-old-archived", "archived": True, "last_edited_time": "2026-02-01T00:00:00Z"},
            {"id": "page-live", "archived": False, "last_edited_time": "2026-02-02T00:00:00Z"},
        ],
    )

    page_id = store._resolve_page_id("demo", "s1", "intent")
    assert page_id == "page-live"


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


def test_save_artifact_fallback_create_parent_uses_typed_database_parent(monkeypatch):
    store = NotionDesignStore(database_id="db123")
    store.tool_names["create_page"] = "fallback-create-tool"
    monkeypatch.setattr(store, "_should_skip_push", lambda *_args, **_kwargs: False)
    monkeypatch.setattr(store, "_resolve_page_id", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(store, "_load_session_context", lambda *_args, **_kwargs: {})
    monkeypatch.setattr(
        store,
        "_build_create_properties",
        lambda **_kwargs: {"properties": {"Stage": {"select": {"name": "Intent"}}}, "content_payload": "hello"},
    )
    monkeypatch.setattr(
        store,
        "_build_update_properties",
        lambda **_kwargs: {"properties": {}, "content_payload": "hello"},
    )
    monkeypatch.setattr(store, "_save_push_metadata", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(store, "_sync_dependencies_to_remote", lambda *_args, **_kwargs: None)

    calls = []

    def fake_call(tool_name, payload):
        calls.append((tool_name, payload))
        return {"id": "page-fallback-typed"}

    monkeypatch.setattr(store, "_call_tool", fake_call)

    store.save_artifact("demo", "s1", "intent", "hello")
    assert calls
    tool_name, payload = calls[0]
    assert tool_name == "fallback-create-tool"
    assert payload["parent"] == {"type": "database_id", "database_id": "db123"}


def test_save_artifact_notion_create_pages_payload_structure(monkeypatch):
    store = NotionDesignStore(database_id="db123")
    store.tool_names["create_page"] = "notion-create-pages"
    monkeypatch.setattr(store, "_should_skip_push", lambda *_args, **_kwargs: False)
    monkeypatch.setattr(store, "_resolve_page_id", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(store, "_load_session_context", lambda *_args, **_kwargs: {})
    monkeypatch.setattr(
        store,
        "_build_create_properties",
        lambda **_kwargs: {
            "properties": {
                "Title": {"title": [{"plain_text": "Intent - s1"}]},
                "Stage": {"select": {"name": "Intent"}},
            },
            "content_payload": "body text",
        },
    )
    monkeypatch.setattr(
        store,
        "_build_update_properties",
        lambda **_kwargs: {"properties": {}, "content_payload": "body text"},
    )
    monkeypatch.setattr(store, "_save_push_metadata", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(store, "_sync_dependencies_to_remote", lambda *_args, **_kwargs: None)

    calls = []

    def fake_call(tool_name, payload):
        calls.append((tool_name, payload))
        return {"id": "page-created-typed"}

    monkeypatch.setattr(store, "_call_tool", fake_call)

    store.save_artifact("demo", "s1", "intent", "body text")
    assert calls
    tool_name, payload = calls[0]
    assert tool_name == "notion-create-pages"
    assert "pages" in payload and isinstance(payload["pages"], list)
    assert payload["parent"] == {"type": "database_id", "database_id": "db123"}
    assert payload["pages"][0]["content"] == "body text"


def test_save_artifact_create_payload_includes_idse_id(monkeypatch):
    store = NotionDesignStore(database_id="db123")
    monkeypatch.setattr(store, "_should_skip_push", lambda *_args, **_kwargs: False)
    monkeypatch.setattr(store, "_resolve_page_id", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(store, "_load_session_context", lambda *_args, **_kwargs: {})
    monkeypatch.setattr(store, "_save_push_metadata", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(store, "_sync_dependencies_to_remote", lambda *_args, **_kwargs: None)
    captured = {"create_props": None}

    def fake_call(tool_name, payload):
        if tool_name == store.tool_names["create_page"]:
            captured["create_props"] = payload.get("pages", [{}])[0].get("properties", {})
            return {"id": "page-create-1"}
        return {"ok": True}

    store.tool_names["create_page"] = "notion-create-pages"
    monkeypatch.setattr(store, "_call_tool", fake_call)

    store.save_artifact("demo", "s1", "intent", "body")
    assert captured["create_props"] is not None
    assert captured["create_props"]["IDSE_ID"] == "demo::s1::intent"


def test_save_artifact_update_path_uses_update_and_replace_not_create(monkeypatch):
    store = NotionDesignStore(database_id="db123")
    monkeypatch.setattr(store, "_should_skip_push", lambda *_args, **_kwargs: False)
    monkeypatch.setattr(store, "_resolve_page_id", lambda *_args, **_kwargs: "existing-page-1")
    monkeypatch.setattr(store, "_load_session_context", lambda *_args, **_kwargs: {})
    monkeypatch.setattr(
        store,
        "_build_create_properties",
        lambda **_kwargs: {"properties": {"Title": {"title": [{"plain_text": "x"}]}}, "content_payload": "new"},
    )
    monkeypatch.setattr(
        store,
        "_build_update_properties",
        lambda **_kwargs: {"properties": {"Stage": {"select": {"name": "Intent"}}}, "content_payload": "new"},
    )
    monkeypatch.setattr(store, "_save_push_metadata", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(store, "_sync_dependencies_to_remote", lambda *_args, **_kwargs: None)

    calls = []

    def fake_call(tool_name, payload):
        calls.append((tool_name, payload))
        return {"ok": True}

    monkeypatch.setattr(store, "_call_tool", fake_call)
    store.save_artifact("demo", "s1", "intent", "new")

    assert calls
    assert all(tool != store.tool_names["create_page"] for tool, _ in calls)
    update_cmds = [payload.get("data", {}).get("command") for tool, payload in calls if tool == store.tool_names["update_page"]]
    assert "replace_content" in update_cmds


def test_save_artifact_update_path_does_not_send_update_properties(monkeypatch):
    store = NotionDesignStore(database_id="db123")
    monkeypatch.setattr(store, "_should_skip_push", lambda *_args, **_kwargs: False)
    monkeypatch.setattr(store, "_resolve_page_id", lambda *_args, **_kwargs: "existing-page-2")
    monkeypatch.setattr(store, "_save_push_metadata", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(store, "_sync_dependencies_to_remote", lambda *_args, **_kwargs: None)

    calls = []

    def fake_call(tool_name, payload):
        calls.append((tool_name, payload))
        return {"ok": True}

    monkeypatch.setattr(store, "_call_tool", fake_call)
    store.save_artifact("demo", "s2", "plan", "updated body")

    prop_payloads = [
        payload
        for tool, payload in calls
        if tool == store.tool_names["update_page"]
        and payload.get("data", {}).get("command") == "update_properties"
    ]
    assert not prop_payloads
