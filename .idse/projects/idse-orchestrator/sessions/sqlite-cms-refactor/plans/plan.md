# Plan — PRD Context Mode
> **This Plan serves as both an Implementation Plan and a Product Requirements Document (PRD).**
> It merges the *product vision* (why we are building this system) with the *technical realization plan* (how it will be implemented).
> It is a canonical artifact of the IDSE pipeline, governed by Articles I–IX of the IDSE Constitution, and must be validated via `idse validate` before implementation.

---

## 0. Product Overview

**Goal / Outcome:**
Move IDSE’s source of truth from files to SQLite while keeping IDE-friendly markdown views.

**Problem Statement:**
File-based state is hard to query and brittle for sync. A SQLite core enables deterministic state, easier migration, and consistent sync semantics.

**Target Users or Use Cases:**
Maintainers and IDE agents needing reliable pipeline state with markdown ergonomics.

**Success Metrics:**
- New sessions stored in SQLite with generated views
- Migration of existing projects without data loss
- CLI commands for export/migrate/query available and usable

## 1. Architecture Summary

Introduce a local SQLite database (`.idse/idse.db`) as the authoritative CMS. Add a DesignStoreSQLite backend and a FileViewGenerator to produce markdown artifacts on demand. Migration tools map existing file artifacts into the database. Sync logic compares hashes from DB artifacts.

## 2. Components

| Component | Responsibility | Interfaces / Dependencies |
| --- | --- | --- |
| `artifact_database.py` | SQLite schema + CRUD | sqlite3 (stdlib) |
| `design_store_sqlite.py` | DesignStore backend | ArtifactDatabase |
| `file_view_generator.py` | Generate markdown views | ArtifactDatabase, filesystem |
| `migration.py` | File → DB migration | File system + ArtifactDatabase |
| CLI additions | export/migrate/query | ProjectWorkspace, ArtifactConfig |

## 3. Data Model

SQLite schema defined in the plan: projects, sessions, artifacts, project_state, agents, agent_stages, collaborators, session_tags.

## 4. API Contracts

CLI-level commands:
- `idse export`: generate markdown view from DB
- `idse migrate`: migrate file projects into SQLite
- `idse query <query>`: run fixed queries (e.g., specs-in-progress, unsynced)

## 5. Test Strategy

- Unit: ArtifactDatabase CRUD and schema creation
- Integration: export generates correct files, migration preserves content
- End-to-end: init → export → validate

## 6. Phases

- Phase 1: Database layer and DesignStoreSQLite
- Phase 2: File view generation + export command
- Phase 3: Migration tooling + migrate command
- Phase 4: Integration updates (init/status/session create/query)
- Phase 5: Sync improvements (hash-based comparison)
