# Notion Backend (MCP)

This backend stores IDSE artifacts in a Notion database using the Notion MCP server.

## Prerequisites

- Node.js + npm (for `npx`)
- Notion MCP server access via `mcp-remote`

## Required Notion Database Properties

Create a database named **IDSE Artifacts** with properties:

- **Project** (rich_text)
- **Session** (rich_text)
- **Stage** (select)
- **IDSE_ID** (rich_text)
- **Title** (title)
- **Body** (page body content)

Stages should align with IDSE stages (intent, context, spec, plan, tasks, implementation, feedback).

## Configuration

Add to `~/.idseconfig.json`:

```json
{
  "artifact_backend": "notion",
  "notion": {
    "database_id": "your-notion-database-id",
    "database_view_id": "optional-database-view-id",
    "database_view_url": "optional-database-view-url",
    "parent_data_source_url": "collection://your-data-source-id",
    "data_source_id": "your-data-source-id",
    "credentials_dir": "./mnt/mcp_credentials",
    "tool_names": {
      "query_database": "notion-query-database-view",
      "create_page": "notion-create-pages",
      "update_page": "notion-update-page",
      "fetch_page": "notion-fetch",
      "append_children": "append_block_children"
    },
    "properties": {
      "idse_id": { "name": "IDSE_ID", "type": "text" },
      "title": { "name": "Title", "type": "title" },
      "project": { "name": "Project", "type": "text" },
      "session": { "name": "Session", "type": "text" },
      "stage": { "name": "Stage", "type": "select" },
      "content": { "name": "body", "type": "page_body" }
    }
  }
}
```

If your MCP server exposes `create_database_item` and `append_block_children`, set:

```json
{
  "tool_names": {
    "create_page": "create_database_item",
    "append_children": "append_block_children"
  }
}
```

If your MCP tool requires a database view ID, set `database_view_id` using the view
identifier from the Notion database URL. The sync layer maps stages to Notion select
values (`Intent`, `Context`, `Specification`, `Plan`, `Tasks`, `Test Plan`, `Feedback`)
to match a typical IDSE Artifacts schema.

## Usage

```bash
idse sync push
idse sync pull
idse sync status
idse sync test
idse sync tools
```

On first use, `mcp-remote` will open a browser for OAuth. Credentials persist in
`./mnt/mcp_credentials` and should be gitignored.
