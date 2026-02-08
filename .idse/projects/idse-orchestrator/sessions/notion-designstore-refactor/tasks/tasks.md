# Tasks

[P] = parallel safe

## Execution Ownership
- Session Owner: `tjpilant`
- Implementation Agent: `gpt-codex`
- Planning Agent: `claude-code`
- Feedback Reviewer: `github-copilot`

## Instructions
- Derive tasks directly from the implementation plan and contracts.
- For each task, note owner, dependencies, and acceptance/validation notes.
- Keep tasks independent and testable; mark parallelizable tasks with [P].
- **These tasks guide the IDE/development team** - they describe what needs to be done, not where code should be written.

## Phase 0 – Schema Foundation
- [x] Task 0.1 – Add `idse_id TEXT UNIQUE` column to `artifacts` table in schema statements (Owner: implementer) (Deps: none) (Acceptance: column exists, schema init works on fresh DB)
- [x] Task 0.2 – Add `artifact_dependencies` table to schema statements (Owner: implementer) (Deps: none) (Acceptance: table created with FK constraints)
- [x] Task 0.3 – Add `sync_metadata` table to schema statements (Owner: implementer) (Deps: none) (Acceptance: table created with unique constraint on artifact_id+backend)
- [x] Task 0.4 – Write migration logic to backfill `idse_id` for existing rows (Owner: implementer) (Deps: 0.1) (Acceptance: all existing artifacts get correct `{project}::{session}::{stage}` value)
- [x] Task 0.5 – Update `save_artifact()` to auto-generate `idse_id` on insert/upsert (Owner: implementer) (Deps: 0.1) (Acceptance: new artifacts get idse_id without caller providing it)
- [x] Task 0.6 – Add `find_by_idse_id()` method to `ArtifactDatabase` (Owner: implementer) (Deps: 0.1) (Acceptance: returns ArtifactRecord or None)
- [x] Task 0.7 – Add `save_dependency()` and `get_dependencies()` methods (Owner: implementer) (Deps: 0.2) (Acceptance: can store and retrieve upstream/downstream links)
- [x] Task 0.8 – Add `save_sync_metadata()` and `get_sync_metadata()` methods (Owner: implementer) (Deps: 0.3) (Acceptance: can track last push/pull hash per backend)
- [x] Task 0.9 [P] – Unit tests for all Phase 0 DB methods and migration (Owner: implementer) (Deps: 0.1-0.8) (Acceptance: all tests pass)
- [x] Task 0.10 [P] – Update `ArtifactRecord` dataclass to include `idse_id` field (Owner: implementer) (Deps: 0.1) (Acceptance: dataclass includes field, all consumers updated)

## Phase 1 – Schema Mapping & Page Lookup
- [x] Task 1.1 – Implement `NotionSchemaMap` class with write modes: `create_only`, `always_sync`, `optional` (Owner: implementer) (Deps: 0.1) (Acceptance: maps spine fields to Notion property dicts with correct mode assignments)
- [x] Task 1.2 – Implement `_build_create_properties()` — full property set for new pages (all modes) and `_build_update_properties()` — excludes `create_only` fields (Owner: implementer) (Deps: 1.1) (Acceptance: Title included on create, excluded on update)
- [x] Task 1.3 – Implement `_resolve_page_id()` — primary lookup via `sync_metadata.remote_id`, fallback to session+stage Notion filter, cache result (Owner: implementer) (Deps: 0.8) (Acceptance: known artifacts resolved without Notion query; first-sync uses filter then caches)
- [x] Task 1.4 – Remove `_ensure_idse_id_property()` and `_query_artifact_page()` (Owner: implementer) (Deps: 1.3) (Acceptance: no forced Notion schema modifications; no IDSE_ID/Title search fallbacks)
- [x] Task 1.5 – Remove `IDSE_ID` and `Project` from `DEFAULT_PROPERTIES` (Owner: implementer) (Deps: 1.4) (Acceptance: push no longer sends IDSE_ID or Project to Notion)
- [x] Task 1.6 – Implement optional computed fields: Layer, Run Scope, Version, Feature/Capability from session tags (Owner: implementer) (Deps: 1.1) (Acceptance: fields included only when tag data exists, skipped otherwise)
- [x] Task 1.7 [P] – Unit tests for `NotionSchemaMap`, write mode splitting, and `_resolve_page_id()` (Owner: implementer) (Deps: 1.1-1.6) (Acceptance: all field projections and lookup paths tested)

## Phase 2 – Hash-Based Sync
- [x] Task 2.1 – Refactor `NotionDesignStore.save_artifact()`: check `sync_metadata.last_push_hash` before pushing, use `_resolve_page_id()` for updates, use `_build_create_properties()` vs `_build_update_properties()` (Owner: implementer) (Deps: 0.8, 1.2, 1.3) (Acceptance: unchanged artifacts skip API call; updates exclude Title)
- [x] Task 2.2 – After successful push: store `remote_id` and `last_push_hash` in `sync_metadata` (Owner: implementer) (Deps: 2.1) (Acceptance: subsequent pushes use cached page ID)
- [x] Task 2.3 – Refactor `NotionDesignStore.load_artifact()`: fetch via `sync_metadata.remote_id`, upsert pulled content into SQLite (Owner: implementer) (Deps: 0.5, 1.3) (Acceptance: pulled content appears in SQLite with correct idse_id and hash)
- [x] Task 2.4 – After successful pull: update `sync_metadata` with `last_pull_hash` and `remote_id` (Owner: implementer) (Deps: 2.3) (Acceptance: pull state tracked per backend)
- [x] Task 2.5 – Update CLI `sync push` to use hash comparison flow (Owner: implementer) (Deps: 2.1, 2.2) (Acceptance: CLI reports skipped/pushed/failed counts)
- [x] Task 2.6 – Update CLI `sync pull` with Notion backend to use upsert flow (Owner: implementer) (Deps: 2.3, 2.4) (Acceptance: pull creates/updates SQLite records)
- [x] Task 2.7 [P] – Integration tests with mock MCP for push/pull with hash comparison (Owner: implementer) (Deps: 2.1-2.6) (Acceptance: tests pass, Title preservation verified)

## Phase 3 – Dependency Sync
- [x] Task 3.1 – On pull: resolve Notion `Upstream Artifact` relation page IDs to `idse_id` values via `sync_metadata` reverse lookup (Owner: implementer) (Deps: 2.3, 0.7) (Acceptance: relations stored in artifact_dependencies)
- [x] Task 3.2 – On push: resolve `artifact_dependencies` to Notion page IDs via `sync_metadata.remote_id` (Owner: implementer) (Deps: 0.7, 1.2) (Acceptance: Notion pages have correct relation links)
- [x] Task 3.3 [P] – Integration tests for dependency round-trip (Owner: implementer) (Deps: 3.1, 3.2) (Acceptance: push deps, pull back, verify match)

## Phase 4 – Hardening
- [x] Task 4.1 – Implement error collection: partial sync failures reported without aborting (Owner: implementer) (Deps: 2.5, 2.6) (Acceptance: sync continues on per-artifact failure, summary printed)
- [x] Task 4.2 – Documentation: Notion sync workflow, schema map reference (Owner: planner) (Deps: all) (Acceptance: docs in implementation/README.md)
- [x] Task 4.3 [P] – Verify all existing tests still pass (Owner: implementer) (Deps: all) (Acceptance: `PYTHONPATH=src pytest -q` green)
