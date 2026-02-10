# Plan: Blueprint Bootstrap Lifecycle

## 0. Product Overview

**Goal:** Enable new IDSE projects to declare founding blueprint claims at bootstrap time, without requiring multi-session convergence evidence.

**Problem:** The promotion gate assumes claims emerge from cross-session patterns. At project init, only `__blueprint__` exists, so no claim can pass. This blocks governance from day one.

**Target Users:** Project architects bootstrapping new IDSE projects; IDE agents that need governance constraints to exist before feature work begins.

**Success Metrics:** A freshly-initialized project can `blueprint declare` founding claims and have them active immediately. All existing promotion/demotion workflows continue unchanged.

## 1. Architecture Summary

The change introduces a **dual-entry claim lifecycle**:

```
                    ┌─────────────────────┐
                    │   BlueprintPromotionGate   │
                    └─────────┬───────────┘
                              │
              ┌───────────────┼───────────────┐
              │                               │
     declare_claim()              evaluate_and_record()
     (bootstrap path)             (convergence path)
              │                               │
              ▼                               ▼
    origin="declared"              origin="converged"
    promotion_record_id=NULL       promotion_record_id=<id>
              │                               │
              └───────────┬───────────────────┘
                          │
                          ▼
                  blueprint_claims (active)
                          │
              ┌───────────┼───────────┐
              │           │           │
         reinforced   superseded  invalidated
         (event only) (status)    (status)
```

Both paths produce `active` claims in `blueprint_claims`. The `origin` column distinguishes provenance. Lifecycle transitions (demotion, supersession) work identically regardless of origin.

## 2. Components

| Component | Responsibility | Changes |
|---|---|---|
| `BlueprintPromotionGate` | Evaluates and manages claim lifecycle | Add `declare_claim()` method |
| `ArtifactDatabase` | SQLite CRUD for claims, lifecycle events | Add `origin` column, make `promotion_record_id` nullable |
| `FileViewGenerator` | Renders `blueprint.md` and `meta.md` | Show origin in rendered views |
| `CLIInterface` (cli.py) | CLI commands for blueprint governance | Add `blueprint declare` command |

## 3. Data Model

### blueprint_claims table — changes

```sql
-- New column (added via _ensure_columns migration)
ALTER TABLE blueprint_claims ADD COLUMN origin TEXT NOT NULL DEFAULT 'converged';

-- promotion_record_id becomes nullable for declared claims
-- Handled by creating new table variant or relaxing constraint
```

### Lifecycle event for declaration

When `declare_claim` is called, record a lifecycle event:
```
old_status: '' (new claim)
new_status: 'active'
reason: 'Founding declaration from blueprint pipeline'
actor: <provided>
```

### Lifecycle event for reinforcement

When a feature session corroborates a declared claim:
```
old_status: 'active'
new_status: 'active' (no change)
reason: 'Reinforced by <session_id>:<stage>'
actor: <system or operator>
```

## 4. API Contracts (Python + CLI)

### Python API

```python
BlueprintPromotionGate.declare_claim(
    project: str,
    *,
    claim_text: str,
    classification: str,
    source_session: str,           # must be __blueprint__
    source_stages: List[str],      # stages in blueprint that evidence the claim
    actor: str = "architect",
) -> Dict[str, Any]
# Returns: {"claim_id": int, "status": "active", "origin": "declared"}

BlueprintPromotionGate.reinforce_claim(
    project: str,
    *,
    claim_id: int,
    reinforcing_session: str,
    reinforcing_stage: str,
    actor: str = "system",
) -> Dict[str, Any]
# Returns: {"claim_id": int, "event": "reinforced", ...}
```

### CLI

```bash
idse blueprint declare \
  --claim "claim text" \
  --classification invariant|boundary|ownership_rule|non_negotiable_constraint \
  --source __blueprint__:intent \
  --source __blueprint__:spec \
  [--actor architect]

idse blueprint reinforce \
  --claim-id 1 \
  --source session_id:stage \
  [--actor system]
```

## 5. Test Strategy

### Unit tests (pytest)

1. `test_declare_claim_creates_active_declared_claim` — happy path
2. `test_declare_claim_rejects_non_blueprint_session` — source must be `__blueprint__`
3. `test_declare_claim_rejects_duplicate_active_claim` — no duplicate claim_text
4. `test_declare_claim_records_lifecycle_event` — event logged
5. `test_declare_claim_with_no_promotion_record` — promotion_record_id is NULL
6. `test_reinforce_claim_records_event_without_status_change` — status stays active
7. `test_reinforce_claim_rejects_nonexistent_claim` — error on bad claim_id
8. `test_existing_promote_workflow_unchanged` — existing tests pass as-is
9. `test_file_view_shows_origin` — blueprint.md distinguishes declared vs converged
10. `test_migration_defaults_existing_claims_to_converged` — schema migration

### Integration tests

- CLI `blueprint declare` end-to-end with file view regeneration
- Mixed declared + converged claims in blueprint.md rendering

## 6. Phases

### Phase 0: Schema Foundation
- Add `origin` column to `blueprint_claims` via `_ensure_columns`
- Make `promotion_record_id` nullable (recreate table if needed, or use new table creation SQL)
- Update `save_blueprint_claim` to accept `origin` and nullable `promotion_record_id`
- Verify all existing tests pass

### Phase 1: Core Declaration Path
- Implement `declare_claim()` on `BlueprintPromotionGate`
- Implement `reinforce_claim()` on `BlueprintPromotionGate`
- Write unit tests for both methods
- Verify existing promotion/demotion tests still pass

### Phase 2: CLI + File Views
- Add `blueprint declare` CLI command
- Add `blueprint reinforce` CLI command
- Update `FileViewGenerator` to render origin in blueprint.md and meta.md
- Write CLI integration tests

### Phase 3: Validation + Cleanup
- Run full test suite
- Verify against a clean `idse init` -> `blueprint declare` workflow
- Update implementation notes and feedback
