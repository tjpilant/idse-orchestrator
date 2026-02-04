# Implementation Readme

Project: idse-orchestrator
Stack: python
Created: 2026-02-02T21:40:24.903118

## What We Implemented

- Notion MCP-backed DesignStore with config-driven sync.
- Sync CLI updates: `idse sync setup`, `sync test`, `sync tools`, `sync describe`, and `sync push/pull`.
- Notion schema mapping with stage normalization and page-body support.
- Debug flag for payload/result visibility during MCP calls.

## MCP Tooling & Payloads (Working)

### Query
Tool: `notion-query-database-view`  
Payload: 
```json
{ "view_url": "view://<view-id-with-dashes>" }
```

### Create Pages
Tool: `notion-create-pages`  
Payload:
```json
{
  "pages": [
    {
      "properties": {
        "Project": "idse-orchestrator",
        "Session": "__blueprint__",
        "Stage": "Intent",
        "Title": "Intent – idse-orchestrator – __blueprint__"
      },
      "content": "# Intent\n\n..."
    }
  ],
  "parent": {
    "type": "database_id",
    "database_id": "<database-id>"
  }
}
```

### Update Content
Tool: `notion-update-page`  
Payload (content):
```json
{
  "data": {
    "page_id": "<page-id>",
    "command": "replace_content",
    "new_str": "# Intent\n\n..."
  }
}
```

Payload (properties):
```json
{
  "data": {
    "page_id": "<page-id>",
    "command": "update_properties",
    "properties": {
      "Project": "idse-orchestrator",
      "Session": "__blueprint__",
      "Stage": "Intent",
      "Title": "Intent – idse-orchestrator – __blueprint__"
    }
  }
}
```

## Notion Schema Requirements

Required properties in the IDSE Artifacts database:
- Project (text)
- Session (text)
- Stage (select)
- Title (title)

Stage select values must be:
`Intent`, `Context`, `Specification`, `Plan`, `Tasks`, `Test Plan`, `Feedback`

## Config (Canonical Example)

```json
{
  "artifact_backend": "notion",
  "notion": {
    "database_id": "<database-id>",
    "database_view_id": "<view-id>",
    "credentials_dir": "./mnt/mcp_credentials",
    "tool_names": {
      "query_database": "notion-query-database-view",
      "create_page": "notion-create-pages",
      "update_page": "notion-update-page",
      "fetch_page": "notion-fetch"
    },
    "properties": {
      "project": { "name": "Project", "type": "text" },
      "session": { "name": "Session", "type": "text" },
      "stage": { "name": "Stage", "type": "select" },
      "title": { "name": "Title", "type": "title" },
      "content": { "name": "page_body", "type": "page_body" }
    }
  }
}
```

## Debug & Verification

- `idse sync test` verifies tool access and schema.
- `idse sync tools --schema` dumps MCP tool schemas.
- `idse sync push --yes --debug` shows payloads and MCP results.

## Boundary: Pipeline Docs vs File Artifacts

Meta and Implementation files are pipeline artifacts and belong here.  
Binary or non-markdown uploads (design assets, datasets, compiled outputs) should be handled
by DesignStore/NotionDesignStore extensions, not by the pipeline docs themselves.
