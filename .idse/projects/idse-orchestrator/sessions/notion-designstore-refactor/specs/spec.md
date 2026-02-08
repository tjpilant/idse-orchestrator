# Specification

## Overview
Refactor `NotionDesignStore` to operate as a view-layer projection of the SQLite spine. Add `idse_id` as a stored column and `artifact_dependencies` as a join table. Formalize the schema mapping between spine fields and Notion properties. Enable bidirectional sync with hash-based change detection.

Predecessor: `sqlite-cms-refactor` (completed 2026-02-07).

## User Stories
- As a maintainer, I want `idse sync push` to skip unchanged artifacts so that Notion sync is fast and idempotent.
- As a maintainer, I want `idse sync pull --backend notion` to import Notion artifacts into SQLite so that my local DB stays current with team edits.
- As a maintainer, I want upstream/downstream artifact relations preserved during sync so that lineage is not lost.
- As a collaborator, I want Notion pages to show computed display fields (Title, Layer, Run Scope) so that the Notion view is human-readable without polluting the spine.

## Functional Requirements
- FR-1: Add `idse_id TEXT UNIQUE` column to `artifacts` table. Generate as `{project}::{session_id}::{stage}`. Backfill existing rows.
- FR-2: Add `artifact_dependencies` join table with `artifact_id`, `depends_on_artifact_id`, `dependency_type`.
- FR-3: Add `sync_metadata` table with `remote_id` to cache Notion page IDs locally. Primary page lookup uses `sync_metadata.remote_id` — no Notion property queries needed for known artifacts.
- FR-4: `NotionDesignStore.save_artifact()` reads `sync_metadata.last_push_hash` before pushing. Skips push if content hash matches. Uses `sync_metadata.remote_id` for page updates (no IDSE_ID/Title search fallback).
- FR-5: `NotionDesignStore.load_artifact()` (pull) writes imported content to SQLite via `ArtifactDatabase.save_artifact()` and updates `sync_metadata`.
- FR-6: Define a `NotionSchemaMap` with property write modes:
  - `create_only`: Title (set on page creation, **never overwritten** — preserves human-authored titles), Session
  - `always_sync`: Stage, Status, content (page body)
  - `optional`: Layer, Run Scope, Version, Feature/Capability (computed from session tags if available)
  - `removed`: IDSE_ID property (no longer needed — replaced by `sync_metadata.remote_id`), Project property (redundant — database = project)
- FR-7: Remove `_ensure_idse_id_property()` — no forced Notion schema modifications.
- FR-8: `idse sync pull` with Notion backend imports artifacts and upserts to SQLite using `sync_metadata.remote_id` as page anchor and `idse_id` as SQLite anchor.
- FR-9: Upstream/downstream Notion relations are resolved to `idse_id` values and stored in `artifact_dependencies`.

### Minimum Required Notion Properties
| Property | Type | Write Mode |
|----------|------|------------|
| Title | title | create_only |
| Stage | select | always_sync |
| Session | rich_text | create_only |
| Status | status | always_sync |
| (page body) | content | always_sync |

## Non-Functional Requirements
- Performance: Hash comparison eliminates unnecessary Notion API calls. A sync of 7 unchanged artifacts should complete in < 2s (only hash checks, no API writes).
- Reliability: Sync failures on individual artifacts do not abort the entire session sync. Errors are collected and reported.
- Compatibility: `DesignStore` abstract interface unchanged. `DesignStoreFilesystem` and `DesignStoreSQLite` unaffected.

## Acceptance Criteria
- AC-1: `idse_id` column exists in `artifacts` table; all existing rows have backfilled values.
- AC-2: `artifact_dependencies` table exists with proper foreign keys.
- AC-3: `sync_metadata` table exists; after first push, `remote_id` contains the Notion page ID.
- AC-4: `idse sync push` with Notion backend skips artifacts whose `content_hash` matches `sync_metadata.last_push_hash`.
- AC-5: `idse sync push` does NOT overwrite Notion Title on update — only sets it on create.
- AC-6: `idse sync push` does NOT require or create `IDSE_ID` or `Project` properties in Notion.
- AC-7: `idse sync pull` with Notion backend creates/updates SQLite artifact records with correct `idse_id`.
- AC-8: Round-trip test: push to Notion, modify in Notion, pull back — content reflects Notion edits.
- AC-9: All existing tests continue to pass.

## Assumptions / Constraints / Dependencies
- Assumptions:
  - Notion MCP server supports `notion-query-database-view`, `notion-create-pages`, `notion-update-page`, `notion-fetch`.
  - Notion database already has Title, Stage, Session, Status properties. No forced schema creation.
- Constraints:
  - No new external dependencies beyond what's already in `pyproject.toml`.
  - SQLite schema changes must be backward-compatible (additive columns, new tables).
  - Notion Title is human-owned — sync must never overwrite it on updates.
- Dependencies:
  - `ArtifactDatabase` (from `sqlite-cms-refactor`).
  - `MCPDesignStoreAdapter` base class.
  - Notion MCP server availability for integration testing.

## Open Questions
- How should Notion relation properties (page ID references) be resolved to `idse_id` during import? Batch-fetch all pages, or lazy-resolve on demand?

## Agent Profile

```yaml
id: notion-designstore-refactor
name: Notion DesignStore Refactor
description: Refactor NotionDesignStore to use SQLite spine as source of truth with hash-based sync and formalized schema mapping.
goals:
  - Add idse_id column, artifact_dependencies table, and sync_metadata table
  - Implement hash-based change detection for Notion push/pull
  - Use sync_metadata.remote_id as primary page lookup (eliminate IDSE_ID/Project Notion properties)
  - Formalize spine-to-Notion schema mapping with property write modes
  - Enable bidirectional Notion sync anchored on sync_metadata.remote_id + idse_id
inputs:
  - Existing NotionDesignStore implementation
  - ArtifactDatabase with content_hash support
  - Notion MCP server tools
outputs:
  - Refactored NotionDesignStore with hash-based sync
  - Schema migration for idse_id and artifact_dependencies
  - NotionSchemaMap for field projection
  - Bidirectional sync via idse sync push/pull
constraints:
  - No changes to DesignStore abstract interface
  - No new external dependencies
  - Backward-compatible schema migration
memory_policy: {}
runtime_hints:
  mode: implementation
version: "1.0"
source_session: notion-designstore-refactor
source_blueprint: __blueprint__
```
