# Feedback

## External / Internal Feedback
- 2026-02-07: Requested mission-report style blueprint rollup capturing both deliverables and lessons learned.
- 2026-02-07: Requested stronger extraction to avoid placeholder noise and overlong bullets in high-level meta view.
- 2026-02-07: Requested explicit split where SQLite is core storage and Notion/filesystem are sync targets only.
- 2026-02-07: Requested command-driven owner/collaborator management to avoid manual `session.json` edits.
- 2026-02-07: Begin execution on `notion-designstore-refactor` with Phase 0 schema prerequisites first.
- 2026-02-07: Proceed with Phase 1 using write-mode-aware Notion schema mapping and cached page ID resolution.

## Impacted Artifacts
- Intent: No changes
- Context: No changes
- Spec: No changes
- Plan / Test Plan: No changes
- Tasks / Implementation: Updated implementation notes with completed metadata-rollup work

## Risks / Issues Raised
- Placeholder-heavy feedback artifacts can pollute rollups if not filtered.
- Narrow section matching misses summaries when teams vary heading style.
- Single `artifact_backend` setting caused status/validation drift by switching storage behavior unintentionally.
- Schema migrations must remain additive for existing local DBs (no destructive table rewrite).

## Actions / Follow-ups
- Populate `notion-designstore-refactor` implementation and feedback artifacts with real content so it appears in blueprint summaries.
- Migrate configs to `storage_backend` + `sync_backend`; keep `artifact_backend` as legacy compatibility only.
- Keep session identity metadata changes behind CLI commands and mirror updates to SQLite.
- Continue with Phase 1 (`NotionSchemaMap`) now that DB primitives are in place.
- Complete remaining Phase 1 cleanup tasks (remove legacy IDSE_ID schema mutation and old page lookup fallback logic).

## Decision Log
- Added `Feedback & Lessons Learned` rollup to blueprint meta.
- Enforced section variants (`Summary`, `Executive Summary`, `Lessons Learned`) and bullet truncation (200 chars).
- Storage/sync split adopted:
  - Storage default remains SQLite (`storage_backend`).
  - Sync target uses independent `sync_backend`.
  - Legacy `artifact_backend=notion` no longer overrides storage backend.
- Session metadata edit path adopted:
  - Owner/collaborators updated via `idse session ...` commands.
  - Changes persisted to `session.json` and mirrored into SQLite (`sessions` + `collaborators` tables).
- Phase 0 schema foundation completed:
  - Added `artifacts.idse_id` and backfill migration.
  - Added `artifact_dependencies` and `sync_metadata`.
  - Added DB methods and tests for IDSE lookup, dependency traversal, and sync hash state.
- Phase 1 progress completed:
  - Added `NotionSchemaMap` write-mode mapping (`create_only`, `always_sync`, `optional`).
  - Added separate create/update property builders so `Title` is create-only.
  - Added `_resolve_page_id()` using `sync_metadata.remote_id` cache with fallback query and cache write-back.
- Removed legacy schema side-effects and broad fallback logic:
  - no forced Notion schema mutation for `IDSE_ID`
  - no title/IDSE_ID workspace search fallback
  - defaults now avoid pushing `IDSE_ID`/`Project` unless explicitly configured

## Pre-Phase-2 Notes
- Phase 0 and Phase 1 are complete and validated; scope is now narrowed to hash-sync semantics and metadata updates.
- Known behavior to preserve in Phase 2:
  - `Title` remains create-only.
  - page targeting should prefer cached `sync_metadata.remote_id`.
  - file artifacts remain generated views of SQLite state.
- Implementation caution:
  - stage/state writes are sequentially applied to avoid race-based status regressions.

## Phase 2 Completion Notes
- Hash-based push skip is now driven by SQLite `sync_metadata.last_push_hash`, not remote content fetch.
- Pull path now writes through SQLite with pull-hash tracking, preserving DB as source of truth.
- Notion page ID cache (`sync_metadata.remote_id`) is now used in both push and pull paths.
- CLI sync reporting now surfaces per-stage failures without aborting the full push loop.

## Phase 3 Completion Notes
- Dependency pull now maps Notion relation page IDs to local artifact IDs via `sync_metadata` reverse lookup.
- Pulled dependency sets replace prior `artifact_dependencies` for deterministic state alignment.
- Dependency push now emits `Upstream Artifact` relation updates using `sync_metadata.remote_id` from upstream artifacts.
- Dependency behavior is covered by tests for both pull mapping and push relation emission.

## Phase 4 Completion Notes
- Sync hardening now treats per-stage read/write failures as non-fatal during `sync pull`, matching existing push behavior.
- CLI output now includes explicit failed-stage summaries for both push and pull paths to aid operator triage.
- Documentation now includes an explicit Notion sync workflow and schema-map reference for future implementation/maintenance passes.

## Live Notion RW Validation (Pre-Closeout)
- Date: 2026-02-08
- Command: `.venv/bin/idse sync test`
  - Result: pass (Notion MCP reachable, required tools available, database reachable).
- Command: `.venv/bin/idse sync pull --project idse-orchestrator --session notion-designstore-refactor --yes`
  - Result: completed, retrieved `0` stage artifacts from Notion for this session.
- Command: `.venv/bin/idse sync push --project idse-orchestrator --session notion-designstore-refactor --yes`
  - Result: did not complete; repeated MCP transport `AbortError` reconnect cycles.
  - Bounded retry with hard timeout exited `124` (timeout), indicating unresolved write-path instability in live MCP session handling.
- Conclusion:
  - Code-path implementation is complete and test-covered.
  - Live Notion write validation is currently blocked by transport instability and must be resolved before final production closeout.

## Live Notion RW Validation (Resolved)
- Date: 2026-02-08
- Notion DB/View used:
  - `https://www.notion.so/2fdffccab9d681599cf9da11e2fe42b7?v=2fdffccab9d681e29775000c06d8e6a2`
- Findings and fixes:
  - `Status` payload shape mismatch for `notion-create-pages` -> flattened status values.
  - IDSE status value mismatch vs Notion options -> mapped to `Draft`, `In Review`, `Locked`, `Superseded`.
  - Missing `remote_id` cache from nested create responses -> expanded page-id extraction.
  - Hash-skip with missing `remote_id` -> skip now disabled until remote id exists.
  - `notion-fetch` payload mismatch (`id` vs `page_id`) -> tool-specific fetch payload with fallback.
- Post-fix live results:
  - `.venv/bin/idse sync push --project idse-orchestrator --session notion-designstore-refactor --yes` -> `Synced 7 stages`
  - `.venv/bin/idse sync pull --project idse-orchestrator --session notion-designstore-refactor --yes` -> `Retrieved 7 stage artifacts`
  - `.venv/bin/pytest -q` -> `60 passed`

## Blueprint Promotion Gate Notes
- Added formal promotion gate checks for Blueprint convergence criteria and persisted decision evidence in SQLite.
- Added explicit CLI path (`idse blueprint promote`) so promotion is deliberate and auditable.
- `blueprint.md` is now generated from allowed promotions and no longer treated as a manual scratch surface.
- `meta.md` now includes promotion records for accepted claims, preserving epistemic lineage.

## Doctrine Alignment Notes
- Added candidate/record split to promotion persistence to align with convergence doctrine language.
- Added structured `feedback_signals` so contradiction/reinforcement can be machine-read without parsing markdown alone.
- Added persisted semantic fingerprints on artifacts to reduce copy-propagation false positives in convergence checks.
- Tightened blueprint write path so routine meta regeneration does not rewrite constitutional scope.


## Amendment Feedback
- Constitution amendment scope now matches implemented behavior: active sessions filtered by status, complete lineage graph rendering, and promotion record dedupe in meta output.
- Remaining follow-up: optionally add supersedes metadata on promotion records to reduce semantic redundancy in historical claims.


## Governance Hardening Feedback
- Resolved prior governance gaps: demotion is now auditable, canonical sections are no longer sticky after demotion, and integrity mismatch handling has explicit event history plus opt-in acceptance.
- Added deterministic lifecycle visibility in `meta.md`, which improves blueprint governance observability for agents and CI workflows.
- Constraint discovered: `blueprint_claims.promotion_record_id` FK requires seeded promotion records in tests; tests were updated to reflect real lifecycle provenance.
