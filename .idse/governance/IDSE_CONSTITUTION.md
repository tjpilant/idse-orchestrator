# IDSE Constitution

The following articles govern the Developer Agent:

## Article I — Intent Supremacy
All decisions must map directly to explicit Intent.

## Article II — Context Alignment
Architectural choices must reflect scale, constraints, compliance, deadlines.

## Article III — Specification Completeness
Agent must not generate plans or code with unresolved ambiguities.

## Article IV — Test-First Mandate
Contracts, integration tests, and behavioral tests must precede implementation.

## Article V — Simplicity & Anti-Abstraction
Favor direct framework use, minimal layers, no unnecessary complexity.

## Article VI — Transparency & Observability
Everything must be explainable, testable, observable.

## Article VII — Plan Before Build
A full implementation plan must exist before generating code.

## Article VIII — Atomic Tasking
Tasks must be independent, testable, parallel where safe.

## Article IX — Feedback Incorporation
Production findings must update Intent, Context, and Specification.

## Article X — Project Bootstrap & Canonical Artifact Mapping

### Section 1 — Purpose
To reduce ambiguity at project creation, the Agency may scaffold a visible project workspace under `projects/<Project>` while preserving the pipeline's canonical artifact locations and auditability.

### Section 2 — Authority
Only the SessionManager (or an approved SessionManager-compatible mechanism) may create or initialize project sessions and the associated folder scaffolding. All session metadata and ownership markers remain authoritative.

### Section 3 — Canonical Artifacts
The canonical locations for pipeline artifacts are now **projects-rooted**:
- Pattern: `projects/<project>/sessions/<session-id>/<stage>/`
- Stages (subdirectories under each session): `intents/`, `contexts/`, `specs/`, `plans/`, `tasks/`, `implementation/`, `feedback/`

**Clarification on `implementation/`:**
- For **IDSE Orchestrator sessions**: Contains validation reports, code examples (in markdown), handoff records, and references to actual code locations
- **NOT** for production code - actual executable code lives in the repository's codebase directories (src/, backend/, frontend/, etc.)
- The IDSE Orchestrator produces **documentation** that the IDE/development team uses to create actual code

Legacy stage-rooted paths (`<stage>/projects/<project>/sessions/<session-id>/...`) are supported only during the grace period defined in Section 6 for backward compatibility and must be flagged by validators when encountered.

### Section 4 — Bootstrap Visibility
Projects MUST record the active session pointer:
- Location: `projects/<Project>/CURRENT_SESSION`
- Content: Records active session-id and canonical root (`projects/<Project>/sessions/<session-id>/`)
- **Status: Authoritative for active session resolution** — canonical artifacts live under the projects-rooted path

### Section 5 — Prohibitions
1. Creating or writing to protected `*/current/*` paths under stage directories is **forbidden**
2. Symlinks named `intents/current` (or similar) are **disallowed** unless created by an approved SessionManager operation and audited
3. Manual creation of session directories without SessionManager is **prohibited**

### Section 6 — Opt-in Remapping
The projects-rooted mapping in Section 3 is the new default. Legacy stage-rooted paths are permitted only during a **time-boxed grace period** with the following conditions:
1. Validators MUST default to projects-rooted resolution and treat stage-rooted usage as legacy, emitting warnings or failures after the grace window.
2. SessionManager MUST scaffold projects-rooted canonicals and MAY emit advisory pointers to legacy locations during grace; removal is mandatory after grace ends.
3. A migration tool with dry-run, audit logs, and rollback MUST be provided to move artifacts from legacy to projects-rooted paths.
4. CI MUST enforce that new artifacts are written to projects-rooted paths after the grace period; legacy writes MUST fail.
5. Any future remap beyond projects-rooted requires a formal amendment, migration plan, approval vote, and backward compatibility guarantees.

### Section 7 — Audit & Trace
All bootstrap actions MUST be recorded:
- Who created the project (user/agent)
- Timestamp
- Session-id
- Audit entry location: `projects/<project>/sessions/<session>/feedback/bootstrap_<project>_<timestamp>.md`
- Included in session history for traceability

### Section 8 — Session Metadata Canonical Location
1. Session-level metadata (owner, collaborators, changelog, project README pointer, review checklist, and related session-scoped docs) MUST be stored under the active session’s metadata directory:  
   `projects/<project>/sessions/<session>/metadata/`
2. All pipeline-driven updates to these metadata files MUST target the metadata directory resolved via the authoritative pointer `projects/<project>/CURRENT_SESSION`.
3. Project-root metadata files MAY exist for discoverability but are read-only; writing to project-root or legacy stage-root metadata locations is **forbidden** after the grace period.
4. Validators and CI MUST warn/fail on missing session metadata or writes to non-canonical metadata locations.

## Article XI — Blueprint Convergence & Metadata Governance

### Section 1 — Blueprint and Meta Authority
1. `blueprint.md` is constitutional scope and contains only converged intent.
2. `meta.md` is a derived runtime oversight report generated from SQLite state.
3. Scope changes are recorded in `blueprint.md`; delivery and status telemetry are recorded in `meta.md`.

### Section 2 — Promotion Gate Requirement
1. New blueprint claims MUST pass the promotion gate before entering `blueprint.md`.
2. Minimum gate checks are mandatory:
   - Session diversity (multi-session evidence)
   - Stage diversity (multi-stage evidence)
   - Feedback survival (no unresolved contradiction)
   - Temporal stability window
3. Every ALLOW decision MUST be persisted with evidence and included in `meta.md` promotion records.

### Section 3 — SQLite Source-of-Truth
1. SQLite is the authoritative store for sessions, artifacts, state, and promotion evidence.
2. Markdown files under `.idse/projects/...` are generated views.
3. Direct markdown edits are non-authoritative unless ingested through approved DB write paths.

### Section 4 — Blueprint Projection Rules
1. `Promoted Converged Intent` in `blueprint.md` is append-only ledger history.
2. Allowed claims MUST also be projected into canonical sections (`Purpose`, `Core Invariants`, etc.) for readability.
3. Projection MUST NOT bypass or replace ledger history.

### Section 5 — Session Registry Semantics
1. `Active Sessions` in `meta.md` includes only sessions with status `draft`, `in_progress`, or `review`, plus `__blueprint__`.
2. Session matrices and lineage views MUST include all known sessions, including `complete` and `archived`.

### Section 6 — Promotion Record Hygiene
1. Presentation of promotion records in `meta.md` MUST dedupe by `claim_text + evidence_hash`, keeping the latest entry.
2. Underlying SQLite records remain immutable audit history.
