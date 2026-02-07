# Tasks

[P] = parallel safe

## Instructions
- Derive tasks directly from the implementation plan and contracts.
- For each task, note owner, dependencies, and acceptance/validation notes.
- Keep tasks independent and testable; mark parallelizable tasks with [P].
- **These tasks guide the IDE/development team** - they describe what needs to be done, not where code should be written.

## Phase 0 – Schema Foundation
- [ ] Task 0.1 – Add `idse_id TEXT UNIQUE` column to `artifacts` table in schema statements (Owner: implementer) (Deps: none) (Acceptance: column exists, schema init works on fresh DB)
- [ ] Task 0.2 – Add `artifact_dependencies` table to schema statements (Owner: implementer) (Deps: none) (Acceptance: table created with FK constraints)
- [ ] Task 0.3 – Add `sync_metadata` table to schema statements (Owner: implementer) (Deps: none) (Acceptance: table created with unique constraint on artifact_id+backend)
- [ ] Task 0.4 – Write migration logic to backfill `idse_id` for existing rows (Owner: implementer) (Deps: 0.1) (Acceptance: all existing artifacts get correct `{project}::{session}::{stage}` value)
- [ ] Task 0.5 – Update `save_artifact()` to auto-generate `idse_id` on insert/upsert (Owner: implementer) (Deps: 0.1) (Acceptance: new artifacts get idse_id without caller providing it)
- [ ] Task 0.6 – Add `find_by_idse_id()` method to `ArtifactDatabase` (Owner: implementer) (Deps: 0.1) (Acceptance: returns ArtifactRecord or None)
- [ ] Task 0.7 – Add `save_dependency()` and `get_dependencies()` methods (Owner: implementer) (Deps: 0.2) (Acceptance: can store and retrieve upstream/downstream links)
- [ ] Task 0.8 – Add `save_sync_metadata()` and `get_sync_metadata()` methods (Owner: implementer) (Deps: 0.3) (Acceptance: can track last push/pull hash per backend)
- [ ] Task 0.9 [P] – Unit tests for all Phase 0 DB methods and migration (Owner: implementer) (Deps: 0.1-0.8) (Acceptance: all tests pass)
- [ ] Task 0.10 [P] – Update `ArtifactRecord` dataclass to include `idse_id` field (Owner: implementer) (Deps: 0.1) (Acceptance: dataclass includes field, all consumers updated)

## Phase 1 – Schema Mapping Layer
- [ ] Task 1.1 – Implement `NotionSchemaMap` class with spine-to-Notion field projection (Owner: implementer) (Deps: 0.1) (Acceptance: maps all spine fields to Notion property dicts)
- [ ] Task 1.2 – Implement computed field generation: Title, Layer, Run Scope, Version, Feature/Capability (Owner: implementer) (Deps: 1.1) (Acceptance: computed fields derived from session metadata and tags)
- [ ] Task 1.3 – Refactor `NotionDesignStore._build_notion_properties()` to use `NotionSchemaMap` (Owner: implementer) (Deps: 1.1, 1.2) (Acceptance: existing push behavior unchanged, properties built via map)
- [ ] Task 1.4 [P] – Unit tests for `NotionSchemaMap` (Owner: implementer) (Deps: 1.1, 1.2) (Acceptance: all field projections tested)

## Phase 2 – Hash-Based Sync
- [ ] Task 2.1 – Refactor `NotionDesignStore.save_artifact()` to check `sync_metadata.last_push_hash` before pushing (Owner: implementer) (Deps: 0.8, 1.3) (Acceptance: unchanged artifacts skip Notion API call)
- [ ] Task 2.2 – Update `save_artifact()` to record `sync_metadata` after successful push (Owner: implementer) (Deps: 2.1) (Acceptance: last_push_hash and remote_id stored)
- [ ] Task 2.3 – Refactor `NotionDesignStore.load_artifact()` to upsert pulled content into SQLite (Owner: implementer) (Deps: 0.5) (Acceptance: pulled content appears in SQLite with correct idse_id and hash)
- [ ] Task 2.4 – Update `sync_metadata` on pull with `last_pull_hash` (Owner: implementer) (Deps: 2.3) (Acceptance: pull state tracked per backend)
- [ ] Task 2.5 – Update CLI `sync push` to use hash comparison flow (Owner: implementer) (Deps: 2.1, 2.2) (Acceptance: CLI reports skipped/pushed counts)
- [ ] Task 2.6 – Update CLI `sync pull` with Notion backend to use upsert flow (Owner: implementer) (Deps: 2.3, 2.4) (Acceptance: pull creates/updates SQLite records)
- [ ] Task 2.7 [P] – Integration tests with mock MCP for push/pull with hash comparison (Owner: implementer) (Deps: 2.1-2.6) (Acceptance: tests pass)

## Phase 3 – Dependency Sync
- [ ] Task 3.1 – On pull: resolve Notion `Upstream Artifact` relation page IDs to `idse_id` values (Owner: implementer) (Deps: 2.3, 0.7) (Acceptance: relations stored in artifact_dependencies)
- [ ] Task 3.2 – On push: resolve `artifact_dependencies` to Notion page IDs for relation properties (Owner: implementer) (Deps: 0.7, 1.3) (Acceptance: Notion pages have correct relation links)
- [ ] Task 3.3 [P] – Integration tests for dependency round-trip (Owner: implementer) (Deps: 3.1, 3.2) (Acceptance: push deps, pull back, verify match)

## Phase 4 – Hardening
- [ ] Task 4.1 – Implement error collection: partial sync failures reported without aborting (Owner: implementer) (Deps: 2.5, 2.6) (Acceptance: sync continues on per-artifact failure, summary printed)
- [ ] Task 4.2 – Documentation: Notion sync workflow, schema map reference (Owner: planner) (Deps: all) (Acceptance: docs in implementation/README.md)
- [ ] Task 4.3 [P] – Verify all existing tests still pass (Owner: implementer) (Deps: all) (Acceptance: `PYTHONPATH=src pytest -q` green)
