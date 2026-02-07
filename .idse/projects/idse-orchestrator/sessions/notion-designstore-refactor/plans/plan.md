# Plan — PRD Context Mode
> **This Plan serves as both an Implementation Plan and a Product Requirements Document (PRD).**
> Predecessor session: `sqlite-cms-refactor` (completed 2026-02-07).
> Governed by Articles I–IX of the IDSE Constitution. Validate via `idse validate` before implementation.

---

## 0. Product Overview

**Goal / Outcome:**
Enable reliable, bidirectional sync between the SQLite spine and Notion as a DesignStore platform. Each platform owns its own schema projection; the spine stays lean.

**Problem Statement:**
The current `NotionDesignStore` was built before SQLite became the source of truth. It doesn't use content hashes for change detection, computes `idse_id` ephemerally, and cannot import from Notion back to SQLite. This causes duplicate pages, missed updates, and one-way-only sync.

**Target Users or Use Cases:**
Maintainers running `idse sync push/pull`, team collaborators viewing artifacts in Notion.

**Success Metrics:**
- Zero duplicate pages on repeated push of unchanged artifacts.
- Successful round-trip: push → edit in Notion → pull → SQLite reflects edits.

## 1. Architecture Summary

```
┌──────────────────────────────────┐
│         SQLite Spine             │
│  artifacts (+ idse_id column)    │
│  artifact_dependencies           │
│  sync_metadata                   │
│  sessions, projects, etc.        │
└──────────────┬───────────────────┘
               │
     ┌─────────┴─────────┐
     │  Sync Engine       │
     │  (hash compare)    │
     │  (idse_id anchor)  │
     └─────────┬──────────┘
               │
     ┌─────────┴──────────┐
     │  NotionSchemaMap    │
     │  spine → Notion     │
     │  projection layer   │
     └─────────┬──────────┘
               │
     ┌─────────┴──────────┐
     │  NotionDesignStore  │
     │  (MCP adapter)      │
     └────────────────────┘
```

Key change: Insert a **schema mapping layer** between the sync engine and the Notion MCP calls. This layer computes derived Notion fields (Title, Layer, etc.) from spine + session data.

## 2. Components

| Component | Responsibility | Interfaces / Dependencies |
| --- | --- | --- |
| `ArtifactDatabase` | Store/retrieve artifacts with `idse_id` and dependencies | `artifact_database.py` — extended |
| `NotionSchemaMap` | Map spine fields → Notion properties; compute derived fields | New class or module |
| `NotionDesignStore` | Push/pull artifacts via Notion MCP using schema map | `design_store_notion.py` — refactored |
| `SyncEngine` (CLI) | Orchestrate push/pull with hash comparison | `cli.py` sync commands — updated |
| `MCPDesignStoreAdapter` | MCP session management | `design_store_mcp.py` — unchanged |

## 3. Data Model

### 3.1 Schema Migration: `artifacts` table

Add `idse_id` column:
```sql
ALTER TABLE artifacts ADD COLUMN idse_id TEXT UNIQUE;
```

Backfill existing rows:
```sql
UPDATE artifacts SET idse_id = (
    SELECT p.name || '::' || s.session_id || '::' || artifacts.stage
    FROM sessions s
    JOIN projects p ON s.project_id = p.id
    WHERE s.id = artifacts.session_id
);
```

### 3.2 New table: `artifact_dependencies`

```sql
CREATE TABLE IF NOT EXISTS artifact_dependencies (
    id INTEGER PRIMARY KEY,
    artifact_id INTEGER NOT NULL,
    depends_on_artifact_id INTEGER NOT NULL,
    dependency_type TEXT NOT NULL DEFAULT 'upstream',
    created_at TEXT NOT NULL,
    UNIQUE(artifact_id, depends_on_artifact_id),
    FOREIGN KEY(artifact_id) REFERENCES artifacts(id) ON DELETE CASCADE,
    FOREIGN KEY(depends_on_artifact_id) REFERENCES artifacts(id) ON DELETE CASCADE
);
```

### 3.3 New table: `sync_metadata`

Track per-artifact, per-backend sync state:
```sql
CREATE TABLE IF NOT EXISTS sync_metadata (
    id INTEGER PRIMARY KEY,
    artifact_id INTEGER NOT NULL,
    backend TEXT NOT NULL,
    last_push_hash TEXT,
    last_push_at TEXT,
    last_pull_hash TEXT,
    last_pull_at TEXT,
    remote_id TEXT,
    UNIQUE(artifact_id, backend),
    FOREIGN KEY(artifact_id) REFERENCES artifacts(id) ON DELETE CASCADE
);
```

### 3.4 NotionSchemaMap — Field Projection

| Spine Field | Notion Property | Type | Source |
| --- | --- | --- | --- |
| `idse_id` | `IDSE_ID` | rich_text | `artifacts.idse_id` |
| `project` | `Project` | rich_text | `projects.name` |
| `session_id` | `Session` | rich_text | `sessions.session_id` |
| `stage` | `Stage` | select | `artifacts.stage` (title-cased) |
| `content` | page body | page_body | `artifacts.content` |
| — | `Title` | title | Computed: `{Stage} – {Project} – {Session}` |
| `status` | `Status` | status | `sessions.status` |
| — | `Layer` | select | From `session_tags` where tag matches layer values |
| — | `Run Scope` | select | From `session_tags` where tag matches scope values |
| — | `Version` | rich_text | From session name or lineage |
| — | `Feature / Capability` | rich_text | From `session_tags` |
| upstream deps | `Upstream Artifact` | relation | `artifact_dependencies` → resolve to Notion page IDs |
| downstream deps | `Downstream Artifact(s)` | relation | Reverse of upstream |

## 4. API Contracts

No new external APIs. Internal method signatures:

### `ArtifactDatabase` additions:
- `save_artifact()` — auto-generates `idse_id` on insert/upsert.
- `save_dependency(artifact_id, depends_on_id, dep_type)` → insert into `artifact_dependencies`.
- `get_dependencies(artifact_id, direction='upstream')` → list of `ArtifactRecord`.
- `find_by_idse_id(idse_id)` → `Optional[ArtifactRecord]`.
- `save_sync_metadata(artifact_id, backend, push_hash, remote_id)` → upsert sync state.
- `get_sync_metadata(artifact_id, backend)` → sync state dict.

### `NotionDesignStore` refactored methods:
- `save_artifact(project, session_id, stage, content)` — queries sync_metadata hash first, skips if unchanged.
- `load_artifact(project, session_id, stage)` — fetches from Notion, upserts to SQLite.
- `_build_notion_properties(artifact, session, tags)` — uses `NotionSchemaMap`.

## 5. Test Strategy

- **Unit**: Test `NotionSchemaMap` field computation in isolation (no MCP).
- **Unit**: Test `ArtifactDatabase` new methods (`find_by_idse_id`, `save_dependency`, `get_dependencies`, sync metadata).
- **Unit**: Test schema migration — verify `idse_id` backfill produces correct values.
- **Integration**: Mock MCP adapter, test full push/pull cycle with hash comparison.
- **Integration**: Test round-trip: push to mock Notion, modify, pull back, verify SQLite reflects changes.
- **Contract**: Verify `DesignStore` interface compliance after refactor.

Tooling: `pytest`, mock MCP sessions.

## 6. Phases

### Phase 0: Schema Foundation
- Add `idse_id` column to `artifacts` with migration.
- Add `artifact_dependencies` table.
- Add `sync_metadata` table.
- Update `ArtifactDatabase` with new methods.
- Backfill existing `idse_id` values.
- Unit tests for all new DB methods.

### Phase 1: Schema Mapping Layer
- Implement `NotionSchemaMap` for spine → Notion field projection.
- Implement computed field generation (Title, Layer, Run Scope, Version).
- Refactor `NotionDesignStore` to use schema map for property building.
- Unit tests for schema map.

### Phase 2: Hash-Based Sync
- Refactor `NotionDesignStore.save_artifact()` to check hash before push.
- Add `sync_metadata` tracking (last_push_hash, remote_id).
- Refactor `NotionDesignStore.load_artifact()` to upsert to SQLite on pull.
- Update CLI `sync push/pull` to use hash comparison.
- Integration tests with mock MCP.

### Phase 3: Dependency Sync
- Resolve Notion relation properties to `idse_id` values on pull.
- Store resolved relations in `artifact_dependencies`.
- On push, resolve `artifact_dependencies` to Notion page IDs for relation properties.
- Integration tests for dependency round-trip.

### Phase 4: Hardening
- Error collection and reporting (partial sync failures).
- Documentation for Notion sync workflow.
- Validate all existing tests still pass.

**Note:** This plan is **documentation** that guides the IDE/development team.
The actual code, schemas, and configurations will be created by the development
team in the appropriate codebase directories (src/, tests/, etc.).
