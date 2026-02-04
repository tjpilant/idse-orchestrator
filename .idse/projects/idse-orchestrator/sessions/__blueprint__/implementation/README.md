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

## Lessons Learned (Verbose)

1) **Notion MCP tool schemas are strict and vary by tool name.**  
   `notion-query-database-view` requires `view_url`, and the accepted format was `view://<dashed-uuid>`. HTTPS view URLs failed.

2) **Database ID vs Data Source ID matters.**  
   For `notion-create-pages`, the correct parent is `parent: { type: "database_id" }` (not `data_source_id`) for this database.

3) **Select values are case-sensitive.**  
   Stage values must match the exact Notion select options. We normalized `intent → Intent`, `spec → Specification`, `implementation → Test Plan`.

4) **Content handling is tool-specific.**  
   `notion-create-pages` accepts a `content` string in Notion Markdown.  
   `notion-update-page` requires `data.command` with `replace_content`.

5) **Visibility depends on view filters.**  
   Pages can exist but be hidden by view filters. Always confirm via raw page URLs returned by MCP.

6) **Debug mode was essential.**  
   Logging payloads and results exposed misaligned schemas and wrong parent types quickly.
