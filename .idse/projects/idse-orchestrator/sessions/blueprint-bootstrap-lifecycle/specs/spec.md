# Specification: Blueprint Bootstrap Lifecycle

## Overview

Extend the blueprint claim lifecycle to support two distinct entry paths: **declaration** (bootstrap, single-session axioms) and **convergence** (cross-session proven patterns). This resolves the circular dependency where blueprint governance requires feature sessions that require blueprint governance.

Traces to: [intent.md](../intents/intent.md), [context.md](../contexts/context.md)

## User Stories

- As a **project architect**, I want to declare founding constraints in `__blueprint__` at project init, so that feature sessions are governed from day one.
- As a **CLI operator**, I want `idse blueprint declare` to create claims without multi-session evidence, so that new projects aren't blocked by convergence gates.
- As a **feature session agent**, I want declared claims to be visible and active, so that I know the project's boundaries before I start work.
- As a **governance auditor**, I want to distinguish declared claims from converged claims, so that I know which constraints are axioms vs proven patterns.

## Functional Requirements

### FR-1: Declare Claim Method

`BlueprintPromotionGate.declare_claim()` — creates a claim with `origin="declared"` that bypasses convergence gates.

- **Input:** `project`, `claim_text`, `classification`, `source_session` (must be `__blueprint__`), `source_stages` (list of stages from blueprint pipeline), `actor`
- **Validation:**
  - `source_session` must be `__blueprint__` (only blueprint can declare)
  - `classification` must be in `CONSTITUTIONAL_CLASSES`
  - `claim_text` must not duplicate an existing active claim
- **Output:** claim_id, lifecycle event recorded with `origin="declared"`
- **Status:** Claim enters as `active` with `origin="declared"`

### FR-2: Origin Column on blueprint_claims

- Add `origin TEXT NOT NULL DEFAULT 'converged'` column to `blueprint_claims` table
- Values: `declared` (bootstrap axiom), `converged` (cross-session promotion)
- Existing claims default to `converged` on migration
- Column added via `_ensure_columns` pattern in `artifact_database.py`

### FR-3: Declaration Promotion Record

- `promotion_record_id` on `blueprint_claims` becomes `NULLABLE`
- Declared claims set `promotion_record_id = NULL` (they didn't go through the promotion gate)
- Converged claims continue to require a promotion record

### FR-4: CLI `blueprint declare`

```
idse blueprint declare \
  --claim "SQLite is the authoritative storage backend" \
  --classification invariant \
  --source __blueprint__:intent __blueprint__:spec \
  [--actor architect]
```

- Sources must reference existing artifacts in the DB
- Regenerates blueprint.md and meta.md file views after declaration
- Outputs claim_id and confirmation

### FR-5: Lifecycle Transitions for Declared Claims

Declared claims support the same demotion paths as converged claims:
- `active` -> `superseded` (via `demote_claim` with superseding_claim_id)
- `active` -> `invalidated` (via `demote_claim` with reason)

Additionally, declared claims can be **reinforced** when feature sessions corroborate them:
- Reinforcement is recorded as a lifecycle event (not a status change)
- The claim stays `active` but gains evidence weight
- Future: reinforced declared claims could auto-promote to `converged` origin once they hit convergence thresholds (out of scope for this session)

### FR-6: File View Updates

- `blueprint.md` — show claim origin in the Promoted Converged Intent section: `[invariant|declared]` vs `[invariant|converged]`
- `meta.md` — promotion record shows `Origin: declared` or `Origin: converged` per claim

### FR-7: save_blueprint_claim Schema Change

- `ArtifactDatabase.save_blueprint_claim()` gains `origin` parameter (default `"converged"`)
- New method `ArtifactDatabase.save_declared_claim()` or extend `save_blueprint_claim` with `promotion_record_id=None` allowed when `origin="declared"`

## Non-Functional Requirements

- No performance regression on promotion gate evaluation
- Schema migration must be non-destructive (ALTER TABLE ADD COLUMN + UPDATE defaults)
- All operations remain deterministic (no LLM calls)

## Acceptance Criteria

- AC-1: `declare_claim` creates an active claim with `origin="declared"` and no promotion_record_id
- AC-2: `declare_claim` rejects non-blueprint source sessions
- AC-3: `declare_claim` rejects duplicate active claims
- AC-4: Existing `evaluate_promotion` and `demote_claim` continue to work unchanged
- AC-5: `blueprint.md` file view distinguishes declared vs converged claims
- AC-6: `meta.md` shows origin in promotion records
- AC-7: CLI `blueprint declare` works end-to-end
- AC-8: All existing 112+ tests pass without modification
- AC-9: New tests cover: declare happy path, reject non-blueprint source, reject duplicate, reinforcement lifecycle event, file view rendering with mixed origins

## Assumptions / Constraints / Dependencies

- Assumes `__blueprint__` session always exists (created by `idse init`)
- Depends on `_ensure_columns` migration pattern for schema changes
- Depends on `FileViewGenerator` for blueprint.md and meta.md rendering

## Component Impact

- **BlueprintPromotionGate** (Operation, parent: ConstitutionRules) — gains `declare_claim` method
- **blueprint_claims schema** (Infrastructure, parent: ConstitutionRules) — gains `origin` column, `promotion_record_id` becomes nullable
- **FileViewGenerator** (Projection, parent: DesignStore) — updated rendering for origin display
- **CLIInterface** (Routing, parent: CLIInterface primitive) — new `blueprint declare` command
