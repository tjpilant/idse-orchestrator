# Intent

## Goal
Refactor `NotionDesignStore` to treat SQLite as the authoritative spine and Notion as a view-layer sync target. Each DesignStore platform owns its own schema projection; the spine remains lean.

## Problem / Opportunity
The current `NotionDesignStore` was built before the SQLite CMS refactor. It operates independently of the SQLite spine:
- It does not consume `content_hash` from SQLite for change detection during push/pull.
- It computes `idse_id` ephemerally instead of reading from a stored column.
- Notion-specific display fields (Layer, Run Scope, Title, Suggested Run Focus) are conflated with spine concerns.
- There is no formalized schema mapping between the SQLite canonical model and Notion's property schema.
- Import (Notion → SQLite) is incomplete; only export works reliably.

## Stakeholders / Users
- Primary users and their goals:
  - **IDSE maintainers**: Reliable bidirectional sync between SQLite and Notion without data loss or duplication.
  - **IDE agents**: Continue reading artifacts from SQLite/filesystem views; Notion sync is transparent.
  - **Team collaborators**: Use Notion as a shared view into pipeline state without worrying about sync drift.

## Success Criteria (measurable)
- Baseline: Notion sync ignores SQLite hashes, duplicates can occur on re-push → Target: Push/pull uses `content_hash` comparison, unchanged artifacts are skipped.
- Baseline: No local cache of Notion page IDs, every push requires search/query → Target: `sync_metadata.remote_id` caches Notion page ID locally, eliminating redundant API lookups.
- Baseline: Push overwrites Notion Title with computed string → Target: Title set on create only, never overwritten on update. Human-authored titles preserved.
- Baseline: Push forces `IDSE_ID` and `Project` properties into Notion schema → Target: Neither required. Page matching uses cached `remote_id`, not Notion property queries.
- Baseline: No import from Notion → Target: `idse sync pull --backend notion` populates SQLite from Notion pages.

## Constraints / Assumptions / Risks
- Business / Compliance: None new.
- Technical:
  - Must not break existing `DesignStore` interface contract.
  - Must not alter the SQLite spine schema beyond adding `idse_id` and `artifact_dependencies`.
  - Notion MCP server API may change; adapter must remain resilient to tool schema variations.
- Known risks:
  - Notion relation properties (Upstream/Downstream) may not map cleanly to SQLite foreign keys without intermediate resolution.
  - MCP tool names and parameter schemas vary between Notion API versions.

## Scope
- In scope:
  - Add `idse_id` column to `artifacts` table with migration.
  - Add `artifact_dependencies` table for upstream/downstream lineage.
  - Add `sync_metadata` table with `remote_id` for Notion page ID caching.
  - Refactor `NotionDesignStore` to use `sync_metadata.remote_id` as primary page lookup (no more IDSE_ID/Project Notion property queries).
  - Remove `_ensure_idse_id_property()` — no longer force-creating Notion schema properties.
  - Implement property write modes: `create_only` (Title), `always_sync` (Stage, Status, content), `optional` (Layer, Run Scope, Version).
  - Implement hash-based change detection in Notion push/pull.
  - Formalize schema mapping: SQLite spine fields → Notion property projections (minimal required set: Title, Stage, Session, Status, page body).
  - Implement Notion → SQLite import for `idse sync pull`.
  - Documentation for Notion sync workflow.
- Out of scope / non-goals:
  - Other DesignStore platforms (GitHub, Linear, etc.).
  - Notion UI customization or formula logic.
  - Changes to the `DesignStore` abstract interface beyond what's needed.
- Dependencies:
  - Completed `sqlite-cms-refactor` session (predecessor).
  - Notion MCP server (`mcp-remote` + `mcp.notion.com`).

## Time / Priority
- Deadline or target release: Next development cycle.
- Criticality / priority: High — required for reliable multi-platform sync.
