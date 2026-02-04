from idse_orchestrator.design_store_notion import NotionDesignStore


def test_notion_property_helpers():
    store = NotionDesignStore(database_id="db123")

    assert store._property_filter("project", "demo") == {
        "property": "Project",
        "rich_text": {"equals": "demo"},
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
    }

    assert _flatten_property_values(properties) == {
        "Title": "Intent",
        "Project": "demo",
        "Stage": "intent",
    }
