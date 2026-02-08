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

Key changes:
1. **`sync_metadata.remote_id`** replaces IDSE_ID/Title-based Notion page lookups. After first push, the Notion page ID is cached locally — no more searching.
2. **Schema mapping layer** between the sync engine and the Notion MCP calls computes derived Notion fields with **write modes** (create_only, always_sync, optional).
3. **IDSE_ID and Project removed** from required Notion properties. Title never overwritten on update.

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

### 3.4 Page Lookup Strategy

**Primary path** (cached, no API call):
```
sync_metadata.remote_id → Notion page ID → direct update
```

**Fallback** (first sync only):
```
Query Notion DB by Session + Stage filter → match → cache remote_id
```

**No longer used**:
- ~~IDSE_ID property query~~
- ~~Title-based search fallback~~
- ~~`notion-search` workspace-wide query~~

### 3.5 NotionSchemaMap — Field Projection with Write Modes

Each field has a **write mode** controlling when it's sent to Notion:

| Notion Property | Type | Write Mode | Source | Notes |
| --- | --- | --- | --- | --- |
| `Title` | title | **create_only** | User-provided or default `{Stage} – {Session}` | Never overwritten on update |
| `Stage` | select | **always_sync** | `artifacts.stage` (title-cased) | Core filtering field |
| `Session` | rich_text | **create_only** | `sessions.session_id` | Immutable per page |
| `Status` | status | **always_sync** | `sessions.status` | Reflects current workflow state |
| (page body) | content | **always_sync** | `artifacts.content` | The artifact markdown |
| `Layer` | select | **optional** | From `session_tags` | Only set if tag data exists |
| `Run Scope` | select | **optional** | From `session_tags` | Only set if tag data exists |
| `Version` | rich_text | **optional** | From session name or lineage | Only set if derivable |
| `Feature / Capability` | rich_text | **optional** | From `session_tags` | Only set if tag data exists |
| `Upstream Artifact` | relation | **optional** | `artifact_dependencies` → resolve to Notion page IDs via `sync_metadata` | Phase 3 |
| `Downstream Artifact(s)` | relation | **optional** | Reverse of upstream | Phase 3 |

**Removed from Notion schema requirements**:
| ~~Property~~ | Reason |
| --- | --- |
| ~~`IDSE_ID`~~ | Replaced by `sync_metadata.remote_id` local cache |
| ~~`Project`~~ | Redundant — Notion database = project scope |

### 3.6 Write Mode Definitions

- **`create_only`**: Set when creating a new Notion page. Excluded from update property sets. Preserves human edits.
- **`always_sync`**: Included in both create and update property sets. Reflects current spine state.
- **`optional`**: Included only when source data is available. Skipped if tags/metadata don't provide a value.

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
- `save_artifact(project, session_id, stage, content)` — checks `sync_metadata.last_push_hash`, skips if unchanged. Uses `sync_metadata.remote_id` for page updates.
- `load_artifact(project, session_id, stage)` — fetches from Notion via `sync_metadata.remote_id`, upserts to SQLite.
- `_resolve_page_id(project, session_id, stage)` — replaces `_query_artifact_page()`. Primary: `sync_metadata.remote_id`. Fallback: session+stage filter (first sync only). Caches result.
- `_build_create_properties(session, stage, tags)` — builds full property set for new pages (all write modes).
- `_build_update_properties(session, stage, tags)` — builds property set for updates (`always_sync` + `optional` only, excludes `create_only`).

### Removed methods:
- `_ensure_idse_id_property()` — no longer force-creates Notion schema properties.
- `_query_artifact_page()` — replaced by `_resolve_page_id()`.

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

### Phase 1: Schema Mapping & Page Lookup
- Implement `NotionSchemaMap` with write modes (`create_only`, `always_sync`, `optional`).
- Implement `_resolve_page_id()` — primary lookup via `sync_metadata.remote_id`, fallback to session+stage filter.
- Implement `_build_create_properties()` and `_build_update_properties()` using write modes.
- Remove `_ensure_idse_id_property()` and `_query_artifact_page()`.
- Remove `IDSE_ID` and `Project` from `DEFAULT_PROPERTIES`.
- Unit tests for schema map and write mode property splitting.

### Phase 2: Hash-Based Sync
- Refactor `NotionDesignStore.save_artifact()` to check `sync_metadata.last_push_hash` before push.
- Use `_resolve_page_id()` for page updates instead of search-based lookup.
- Cache `remote_id` in `sync_metadata` after create/update.
- Refactor `NotionDesignStore.load_artifact()` to upsert to SQLite on pull and update `sync_metadata`.
- Update CLI `sync push/pull` to use hash comparison and report skip/push counts.
- Integration tests with mock MCP.

### Phase 3: Dependency Sync
- Resolve Notion relation properties to `idse_id` values on pull (via `sync_metadata` page-ID-to-idse_id mapping).
- Store resolved relations in `artifact_dependencies`.
- On push, resolve `artifact_dependencies` to Notion page IDs via `sync_metadata.remote_id`.
- Integration tests for dependency round-trip.

### Phase 4: Hardening
- Error collection and reporting (partial sync failures).
- Documentation for Notion sync workflow.
- Validate all existing tests still pass.

**Note:** This plan is **documentation** that guides the IDE/development team.
The actual code, schemas, and configurations will be created by the development
team in the appropriate codebase directories (src/, tests/, etc.).
