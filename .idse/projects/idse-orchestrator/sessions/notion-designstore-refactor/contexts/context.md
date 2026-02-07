# Context

## 1. Environment

- **Product / Project:** IDSE Orchestrator — the CLI and runtime for Intent-Driven Systems Engineering.
- **Domain:** Developer tooling / design-time pipeline management.
- **Users / Actors:**
  - IDSE maintainers who run `idse sync push/pull` to synchronize artifacts.
  - IDE agents (Claude Code, Copilot, Codex) that read artifacts from SQLite/filesystem.
  - Team collaborators who view and edit pipeline artifacts in Notion.

## 2. Stack

- **Backend / API:** Python 3.11+, Click CLI, stdlib sqlite3.
- **Database / Storage:**
  - SQLite (`idse.db`) — authoritative local spine.
  - Filesystem (`.idse/projects/`) — generated markdown views.
  - Notion (remote) — collaborative view-layer via MCP.
- **Integrations:**
  - Notion MCP server via `mcp-remote` (`mcp.notion.com/mcp`).
  - MCP Python SDK (`mcp` package) for `StdioServerParameters`, `ClientSession`.

## 3. Constraints

- **Scale:** Single-project, single-user sync at a time. No concurrent push/pull.
- **Performance:** Sync latency is dominated by Notion MCP round-trips. Hash comparison should eliminate unnecessary API calls.
- **Legacy Considerations:**
  - `DesignStore` abstract interface (`load_artifact`, `save_artifact`, `list_sessions`, `load_state`, `save_state`) must remain stable.
  - `MCPDesignStoreAdapter` base class provides MCP session management — not to be modified unless necessary.
  - `NotionDesignStore.DEFAULT_PROPERTIES` defines current field mappings — must be extended, not replaced.
  - Existing `_make_idse_id()` function computes `{project}::{session}::{stage}` — this becomes the stored format.

## 4. Risks & Unknowns

- **Technical Risks:**
  - Notion MCP `notion-query-database-view` tool returns all rows; client-side filtering is already implemented but may not scale.
  - Relation properties (`Upstream Artifact`, `Downstream Artifact(s)`, `Component(s)`) return Notion page IDs, not IDSE IDs. Resolving these requires additional page fetches.
  - The `notion-update-data-source` tool for adding properties may fail silently or be unavailable on some Notion workspaces.
- **Unknowns:**
  - Exact MCP tool parameter schema for current Notion MCP server version.
  - Whether Notion relations can be set via `notion-create-pages` / `notion-update-page` or require separate API calls.
  - How to handle Notion formula fields (`Run Focus OK`) during import — likely skip.
