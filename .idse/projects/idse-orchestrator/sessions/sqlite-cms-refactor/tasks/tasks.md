# Tasks

[P] = parallel safe

## Instructions
- Derive tasks directly from the implementation plan and contracts.
- For each task, note owner, dependencies, and acceptance/validation notes.
- Keep tasks independent and testable; mark parallelizable tasks with [P].
- **These tasks guide the IDE/development team** - they describe what needs to be done, not where code should be written.

## Phase 1 – Database Layer
- [ ] Task 1.1 – Define SQLite schema and create `ArtifactDatabase` (Owner: implementer) (Deps: none) (Acceptance: schema created and CRUD works)
- [ ] Task 1.2 – Implement `DesignStoreSQLite` using `ArtifactDatabase` (Owner: implementer) (Deps: 1.1) (Acceptance: DesignStore interface methods pass tests)
- [ ] Task 1.3 [P] – Unit tests for DB CRUD and schema initialization (Owner: implementer) (Deps: 1.1) (Acceptance: tests pass)

## Phase 2 – File View Generation
- [ ] Task 2.1 – Implement `FileViewGenerator` for session/project views (Owner: implementer) (Deps: 1.1) (Acceptance: files generated match DB content)
- [ ] Task 2.2 – Add `idse export` CLI command (Owner: implementer) (Deps: 2.1) (Acceptance: export regenerates markdown views)

## Phase 3 – Migration Tools
- [ ] Task 3.1 – Implement `FileToDatabaseMigrator` (Owner: implementer) (Deps: 1.1) (Acceptance: migration imports artifacts)
- [ ] Task 3.2 – Add `idse migrate` CLI command (Owner: implementer) (Deps: 3.1) (Acceptance: migration runs without data loss)

## Phase 4 – Integration
- [ ] Task 4.1 – Update `idse init` to create DB records and generate views (Owner: implementer) (Deps: 1.1, 2.1)
- [ ] Task 4.2 – Update `idse session create` and `idse status` to read from DB when backend is sqlite (Owner: implementer) (Deps: 1.2)
- [ ] Task 4.3 – Add `idse query` commands for fixed queries (Owner: implementer) (Deps: 1.1)

## Phase 5 – Sync Alignment
- [ ] Task 5.1 – Update Notion sync to use DB hash comparison (Owner: implementer) (Deps: 1.1) (Acceptance: push/pull uses hashes from DB)
- [ ] Task 5.2 [P] – Update docs to describe sqlite backend and migration (Owner: implementer) (Deps: 1.1)
