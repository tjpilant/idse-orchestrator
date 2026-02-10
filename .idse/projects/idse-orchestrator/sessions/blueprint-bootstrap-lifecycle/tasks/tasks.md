# Tasks: Blueprint Bootstrap Lifecycle

[P] = parallel safe

## Phase 0 — Schema Foundation

- [x] Task 0.1 — Add `origin` column to `blueprint_claims` table
  - Owner: implementation agent
  - Deps: none
  - File: `src/idse_orchestrator/artifact_database.py`
  - Details: Add to `_ensure_columns()`: check for `origin` column on `blueprint_claims`, if missing `ALTER TABLE blueprint_claims ADD COLUMN origin TEXT NOT NULL DEFAULT 'converged'`
  - Acceptance: Column exists, existing claims default to `converged`, all existing tests pass

- [x] Task 0.2 — Make `promotion_record_id` nullable on `blueprint_claims` [P]
  - Owner: implementation agent
  - Deps: none
  - File: `src/idse_orchestrator/artifact_database.py`
  - Details: Created `_migrate_blueprint_claims_nullable_promotion_record()` to handle existing DBs with NOT NULL constraint via table rename/recreate pattern. New schema uses `promotion_record_id INTEGER` (nullable).
  - Acceptance: New claims can be saved with `promotion_record_id=None`, existing claims unaffected

- [x] Task 0.3 — Update `save_blueprint_claim` to accept `origin` parameter [P]
  - Owner: implementation agent
  - Deps: Task 0.1
  - File: `src/idse_orchestrator/artifact_database.py`
  - Details: Added `origin: str = "converged"` parameter. Included in INSERT and ON CONFLICT UPDATE. `promotion_record_id` changed to `Optional[int]`.
  - Acceptance: `save_blueprint_claim(origin="declared")` stores `declared` in DB

- [x] Task 0.4 — Run existing test suite to verify no regressions
  - Owner: implementation agent
  - Deps: Tasks 0.1, 0.2, 0.3
  - Acceptance: 127 tests pass (112 original + 15 new)

## Phase 1 — Core Declaration Path

- [x] Task 1.1 — Implement `declare_claim()` on `BlueprintPromotionGate`
  - Owner: implementation agent
  - Deps: Phase 0
  - File: `src/idse_orchestrator/blueprint_promotion.py`
  - Acceptance: AC-1, AC-2, AC-3 from spec — verified by tests

- [x] Task 1.2 — Implement `reinforce_claim()` on `BlueprintPromotionGate` [P]
  - Owner: implementation agent
  - Deps: Phase 0
  - File: `src/idse_orchestrator/blueprint_promotion.py`
  - Acceptance: Lifecycle event recorded, status unchanged — verified by tests

- [x] Task 1.3 — Write unit tests for `declare_claim`
  - Owner: implementation agent
  - Deps: Task 1.1
  - File: `tests/test_blueprint_claims.py`
  - Tests: 6 tests implemented and passing
  - Acceptance: All new tests pass, all existing tests pass

- [x] Task 1.4 — Write unit tests for `reinforce_claim` [P]
  - Owner: implementation agent
  - Deps: Task 1.2
  - File: `tests/test_blueprint_claims.py`
  - Tests: 3 tests implemented and passing
  - Acceptance: All new tests pass

## Phase 2 — CLI + File Views

- [x] Task 2.1 — Add `blueprint declare` CLI command
  - Owner: implementation agent
  - Deps: Task 1.1
  - File: `src/idse_orchestrator/cli.py` (line 1183)
  - Acceptance: AC-7 from spec — verified by CLI test

- [x] Task 2.2 — Add `blueprint reinforce` CLI command [P]
  - Owner: implementation agent
  - Deps: Task 1.2
  - File: `src/idse_orchestrator/cli.py` (line 1271)
  - Acceptance: CLI works end-to-end — verified by CLI test

- [x] Task 2.3 — Update `FileViewGenerator` to show claim origin
  - Owner: implementation agent
  - Deps: Task 0.3
  - File: `src/idse_orchestrator/file_view_generator.py`
  - Acceptance: AC-5, AC-6 from spec — verified by tests

- [x] Task 2.4 — Write file view tests
  - Owner: implementation agent
  - Deps: Tasks 2.3, 1.1
  - File: `tests/test_blueprint_claims.py`
  - Tests: 3 tests implemented and passing
  - Acceptance: AC-5, AC-6 verified

## Phase 3 — Validation + Cleanup

- [x] Task 3.1 — Run full test suite
  - Owner: implementation agent
  - Deps: All above
  - Acceptance: 127 tests passing

- [x] Task 3.2 — Write implementation/README.md
  - Owner: implementation agent
  - Deps: All above
  - Acceptance: Documents what was built, component impact report

- [x] Task 3.3 — Write feedback/feedback.md
  - Owner: implementation agent
  - Deps: All above
  - Acceptance: Lessons learned, issues, suggestions for blueprint
