# idse-orchestrator - Blueprint Meta

## Session Registry

This document tracks all sessions spawned from this Blueprint.

### Active Sessions
- `__blueprint__` (THIS SESSION) - Project governance and roadmap
- `designstore-file-artifacts` - Feature session
- `item8-test-session` - Feature session
- `blueprint-bootstrap-lifecycle` - Feature session

## Session Status Matrix

| Session ID | Type | Status | Owner | Created | Progress |
|------------|------|--------|-------|---------|----------|
| __blueprint__ | blueprint | draft | system | 2026-02-04 | 0% |
| designstore-file-artifacts | feature | draft | system | 2026-02-04 | 0% |
| sqlite-cms-refactor | feature | complete | system | 2026-02-04 | 100% |
| notion-designstore-refactor | feature | complete | tjpilant | 2026-02-07 | 100% |
| item8-test-session | feature | draft | system | 2026-02-09 | 0% |
| component-impact-parser | feature | complete | system | 2026-02-10 | 100% |
| agent-spec-compiler | feature | complete | system | 2026-02-10 | 100% |
| blueprint-bootstrap-lifecycle | feature | draft | system | 2026-02-13 | 0% |

## Lineage Graph

```
__blueprint__ (root)
├── agent-spec-compiler
├── blueprint-bootstrap-lifecycle
├── component-impact-parser
├── designstore-file-artifacts
├── item8-test-session
├── notion-designstore-refactor
└── sqlite-cms-refactor
```

## Governance

Authoritative scope is defined in `blueprint.md`.
- `meta.md` is derived from runtime session state in SQLite.
- Use `blueprint.md` to define or change project intent, constraints, and invariants.
- Use `meta.md` to monitor delivery, feedback, and alignment across sessions.

## Feedback Loop

Feedback from Feature Sessions flows upward to inform Blueprint updates.

## Delivery Summary

- `sqlite-cms-refactor`: Implemented SQLite core storage via `ArtifactDatabase`.; Added `DesignStoreSQLite` backend and config support.; Added unit tests for SQLite CRUD and schema creation.; Added `FileViewGenerator` and `idse export` command.; Added file-to-DB migration tooling and `idse migrate` command.
- `notion-designstore-refactor`: Enhanced blueprint metadata rollup to include delivery and feedback lessons from SQLite artifacts.; Hardened markdown section extraction to support `#`, `##`, `###`, and `Executive Summary` variants.; Refactored backend semantics: SQLite is now treated as storage core while sync uses a separate `sync_backend`.; Added session metadata management commands to avoid direct JSON edits:; `idse session set-owner`
- `item8-test-session`: **ComponentName** (source_module.py); Parent Primitives: PrimitiveA, PrimitiveB; Type: Projection/Operation/Infrastructure/Routing; Changes: [brief description]; **NewComponentName** (source_module.py)
- `component-impact-parser`: Updated validation engine to enforce implementation artifact quality:; `src/idse_orchestrator/validation_engine.py`; `implementation.md` is validated as a first-class artifact.; Placeholder markers now fail validation.; `Component Impact Report` section and component entries are required.
- `agent-spec-compiler`: `models.py` — ObjectiveFunction, CoreTask, AuthorityBoundary, OutputContract, MissionContract, PersonaOverlay, AgentSpecProfilerDoc (with `schema_version: str = "1.0"`); `error_codes.py` — 22 canonical error codes with stable numeric IDs (E1000-E1018, W2001-W2002); `validate.py` — Enforcement rules engine with 8 detection functions; `map_to_agent_profile_spec.py` — Deterministic mapper (zero inference); `cli.py` — Interactive 20-question intake + 3-phase pipeline

## Feedback & Lessons Learned

- `sqlite-cms-refactor`: Stored project state as JSON in SQLite for parity with legacy `session_state.json`.; Clarify defaults: SQLite is default for new projects; filesystem is legacy/explicit opt-in.; Session state file should become a generated view of CURRENT_SESSION state from SQLite.
- `notion-designstore-refactor`: **MCP Parameter Discovery**: Use `mcp_github` tools for code, but rely on `describe` or direct schema fetches for Notion. The Notion API shapes for `parent` (needs explicit `type: database_id`) and...; **Status Property Shape**: Notion's `status` property is an object, not a simple string. Flattening payloads for `create_page` vs `update_page` required distinct handling.; **Fallback Parent Format**: The initial implementation assumed `parent: { database_id: ... }` was sufficient, but `parent: { type: "database_id", database_id: ... }` is strictly required.
- `component-impact-parser`: Decision: Keep enforcement guardrails; do not reintroduce parser/database component-sync feature in this session.; Decision: Accept implementation report as sufficient session output for governance and handoff.; Decision: Storage-side agents own operational use of report data post-closeout.
- `agent-spec-compiler`: Pydantic v2 schema constraints create a "two-layer" validation boundary. Design error codes knowing which layer catches which violation.; Document generation from structured data requires careful prose quality. Template-based generation produces acceptable but formulaic output.; End-to-end integration tests (profiler → spec.md → compiler → .profile.yaml) are the most valuable tests in the suite — they catch interface mismatches between independently developed components.; Stable numeric error code IDs (E1000-E1018, W2001-W2002) enable future tooling (IDE integrations, CI scripts) without string parsing.; Decision: Implement profiler as separate pre-compiler package (`src/idse_orchestrator/profiler/`) instead of folding into compiler package.

## Blueprint Promotion Record

- Date: 2026-02-08T04:54:05.757638
  Promoted Claim: IDSE Orchestrator is the design-time Documentation OS for project intent and delivery.
  Classification: non_negotiable_constraint
  Origin: converged
  Source Sessions: __blueprint__, designstore-file-artifacts
  Source Stages: context, intent
  Feedback Artifacts: idse-orchestrator::__blueprint__::feedback, idse-orchestrator::designstore-file-artifacts::feedback
  Evidence Hash: 91ecf19533a1788986addd301c46195dbcda779e5212ca12bafc8c7bb80807ca
  Lifecycle: active
- Date: 2026-02-08T04:50:57.556902
  Promoted Claim: SQLite is the authoritative storage backend for project artifacts.
  Classification: invariant
  Origin: converged
  Source Sessions: notion-designstore-refactor, sqlite-cms-refactor
  Source Stages: feedback, spec
  Feedback Artifacts: idse-orchestrator::notion-designstore-refactor::feedback, idse-orchestrator::sqlite-cms-refactor::feedback
  Evidence Hash: 75f04365ac4539d9e02bd66fc1fdcfd59214bce6639377ce21b980256ee46ebc
  Lifecycle: active
- Date: 2026-02-08T04:29:31.463611
  Promoted Claim: SQLite is the default storage backend for project artifacts.
  Classification: invariant
  Origin: converged
  Source Sessions: notion-designstore-refactor, sqlite-cms-refactor
  Source Stages: feedback, spec
  Feedback Artifacts: idse-orchestrator::notion-designstore-refactor::feedback, idse-orchestrator::sqlite-cms-refactor::feedback
  Evidence Hash: 4b6a41e196af071dfb1382af33bfa0e31de088e458d9200c6342840b77787d96
  Lifecycle: active

## Demotion Record

- No demotion events recorded.

## Meta Narrative

<!-- BEGIN CUSTOM NARRATIVE -->
### Known Gaps

- **`idse init --force`**: No way to restart a partial init (e.g., Ctrl-C during `--guided`). `init_project()` raises `ValueError` if project dir exists. Need either `--force` flag on init, an `idse destroy <project>` command, or partial-init detection with resume/restart.
- **CURRENT_SESSION drift**: Session pointer can revert to a stale value after branch switches or DB state changes. The file and DB pointer need better synchronization guards.
<!-- END CUSTOM NARRATIVE -->

---
*Last updated: 2026-02-13T17:03:16.924553*
