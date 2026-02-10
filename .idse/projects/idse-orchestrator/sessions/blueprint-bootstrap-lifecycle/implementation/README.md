# Implementation: idse-orchestrator

Session: blueprint-bootstrap-lifecycle
Stack: python
Created: 2026-02-10

## Architecture

This implementation introduces a dual-entry claim lifecycle in `BlueprintPromotionGate`:

- `declare_claim()` creates bootstrap claims directly in `blueprint_claims` with `origin="declared"` and `promotion_record_id=NULL`.
- `evaluate_and_record()` remains the existing convergence path and continues to produce claims with `origin="converged"`.
- `reinforce_claim()` records corroboration as lifecycle events (`active -> active`) without status transitions.

Storage now explicitly tracks claim provenance (`origin`) and supports declaration-origin claims by allowing nullable promotion records.

## What Was Built

- Updated `blueprint_claims` schema handling in `ArtifactDatabase`:
  - Added `origin` column migration (`default='converged'`).
  - Made `promotion_record_id` nullable in canonical schema.
  - Added migration path that rebuilds legacy `blueprint_claims` tables where `promotion_record_id` was `NOT NULL`.
  - Extended `save_blueprint_claim()` to accept `origin` and nullable `promotion_record_id`.
- Added new lifecycle APIs in `BlueprintPromotionGate`:
  - `declare_claim(...)`
  - `reinforce_claim(...)`
- Added CLI commands:
  - `idse blueprint declare`
  - `idse blueprint reinforce`
- Updated file views:
  - `blueprint.md` now renders claim ledger entries as `[classification|origin]`.
  - `meta.md` promotion record now includes `Origin:` per claim and includes declared claims without promotion records.
- Added/updated tests for:
  - declaration and reinforcement behaviors,
  - origin rendering in views,
  - CLI declare/reinforce flows,
  - schema migration defaults for legacy claims.

## Validation Reports

- Command: `PYTHONPATH=src pytest -q`
- Result: `127 passed in 33.85s`

Additional targeted runs were executed during implementation for:
- `tests/test_artifact_database.py`
- `tests/test_blueprint_promotion.py`
- `tests/test_blueprint_claims.py`
- `tests/test_cli.py`

## Deviations from Plan

- No architectural deviations.
- Minor implementation detail: to safely support existing databases with `promotion_record_id NOT NULL`, a table-rebuild migration was implemented in `_ensure_columns()` instead of relying on insert-time behavior.

## Component Impact Report

- **BlueprintPromotionGate** (`src/idse_orchestrator/blueprint_promotion.py`) — Modified — Operation — Parent: `ConstitutionRules`
- **blueprint_claims schema** (`src/idse_orchestrator/artifact_database.py`) — Modified — Infrastructure — Parent: `ConstitutionRules`
- **CLIInterface** (`src/idse_orchestrator/cli.py`) — Modified — Routing — Parent: `CLIInterface`
- **FileViewGenerator** (`src/idse_orchestrator/file_view_generator.py`) — Modified — Projection — Parent: `DesignStore`
- **Test coverage** (`tests/test_blueprint_claims.py`, `tests/test_cli.py`, `tests/test_file_view_generator.py`, `tests/test_artifact_database.py`) — Modified — Artifact — Parent: `ConstitutionRules`

### Files Edited (no component mapping)

- None
