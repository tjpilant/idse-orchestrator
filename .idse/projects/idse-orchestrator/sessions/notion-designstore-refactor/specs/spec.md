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
- FR-3: `NotionDesignStore.save_artifact()` reads `content_hash` from SQLite before pushing. Skips push if remote content matches hash.
- FR-4: `NotionDesignStore.load_artifact()` (pull) writes imported content to SQLite via `ArtifactDatabase.save_artifact()`.
- FR-5: Define a `NotionSchemaMap` that maps spine fields to Notion property names/types, including computed fields:
  - `title` → computed: `{Stage} – {Project} – {Session}`
  - `status` → from `sessions.status`
  - `layer`, `run_scope` → from `session_tags`
  - `version` → derived from session lineage
- FR-6: `idse sync pull` with Notion backend imports artifacts and upserts to SQLite using `idse_id` as anchor.
- FR-7: Upstream/downstream Notion relations are resolved to `idse_id` values and stored in `artifact_dependencies`.

## Non-Functional Requirements
- Performance: Hash comparison eliminates unnecessary Notion API calls. A sync of 7 unchanged artifacts should complete in < 2s (only hash checks, no API writes).
- Reliability: Sync failures on individual artifacts do not abort the entire session sync. Errors are collected and reported.
- Compatibility: `DesignStore` abstract interface unchanged. `DesignStoreFilesystem` and `DesignStoreSQLite` unaffected.

## Acceptance Criteria
- AC-1: `idse_id` column exists in `artifacts` table; all existing rows have backfilled values.
- AC-2: `artifact_dependencies` table exists with proper foreign keys.
- AC-3: `idse sync push` with Notion backend skips artifacts whose `content_hash` matches the last-pushed hash.
- AC-4: `idse sync pull` with Notion backend creates/updates SQLite artifact records with correct `idse_id`.
- AC-5: Notion pages include computed Title, and optional Layer/Run Scope/Version fields when data is available.
- AC-6: Round-trip test: push to Notion, modify in Notion, pull back — content reflects Notion edits.
- AC-7: All existing tests continue to pass.

## Assumptions / Constraints / Dependencies
- Assumptions:
  - Notion MCP server supports `notion-query-database-view`, `notion-create-pages`, `notion-update-page`, `notion-fetch`.
  - `idse_id` format `{project}::{session_id}::{stage}` is globally unique within a single Notion database.
- Constraints:
  - No new external dependencies beyond what's already in `pyproject.toml`.
  - SQLite schema changes must be backward-compatible (additive columns, new tables).
- Dependencies:
  - `ArtifactDatabase` (from `sqlite-cms-refactor`).
  - `MCPDesignStoreAdapter` base class.
  - Notion MCP server availability for integration testing.

## Open Questions
- How should Notion relation properties (page ID references) be resolved to `idse_id` during import? Batch-fetch all pages, or lazy-resolve on demand?
- Should a `last_push_hash` be stored per-artifact to distinguish "never pushed" from "pushed but unchanged"?

## Agent Profile

```yaml
id: notion-designstore-refactor
name: Notion DesignStore Refactor
description: Refactor NotionDesignStore to use SQLite spine as source of truth with hash-based sync and formalized schema mapping.
goals:
  - Add idse_id column and artifact_dependencies table
  - Implement hash-based change detection for Notion push/pull
  - Formalize spine-to-Notion schema mapping
  - Enable bidirectional Notion sync anchored on idse_id
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
