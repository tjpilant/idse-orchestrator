# Context: Blueprint Bootstrap Lifecycle

## 1. Environment

- **Product / Project:** IDSE Orchestrator — the design-time Documentation OS for Intent-Driven Systems Engineering
- **Domain:** Developer tooling, governance, pipeline orchestration
- **Users / Actors:** Project architects declaring founding constraints; IDE agents (Claude Code, GPT Codex) operating under claim governance; `idse` CLI operators managing claim lifecycle

## 2. Stack

- **Language:** Python 3.10+
- **Storage:** SQLite (`idse.db`) — source of truth for all artifacts, claims, lifecycle events
- **CLI Framework:** Click 8.1+
- **File Views:** `FileViewGenerator` renders `blueprint.md` and `meta.md` from DB state
- **Promotion Engine:** `BlueprintPromotionGate` in `blueprint_promotion.py` — evaluates and records claim promotions/demotions

## 3. Constraints

### Current Promotion Gate Rules (the problem surface)

| Gate Check | Requirement | Bootstrap Impact |
|---|---|---|
| `INSUFFICIENT_SESSION_DIVERSITY` | `len(distinct_sessions) >= 2` | Fails — only `__blueprint__` exists |
| `INSUFFICIENT_STAGE_DIVERSITY` | `len(distinct_stages) >= 2` | May pass if blueprint has intent + spec |
| `INSUFFICIENT_TEMPORAL_STABILITY` | `(max_ts - min_ts).days >= 7` | Fails — all artifacts created same day |
| `NO_FEEDBACK_EVIDENCE` | At least 1 feedback artifact | Fails — no feature sessions to provide feedback |
| `CONTRADICTED_BY_FEEDBACK` | No contradiction markers | N/A at bootstrap |
| `NOT_CONSTITUTIONAL` | Classification in allowed set | Unaffected |
| `DUPLICATE_STATEMENT` | Pairwise similarity < 0.98 | Unaffected |

### DB Schema Constraints

- `blueprint_claims` table has `promotion_record_id INTEGER NOT NULL` — every claim currently must link to a promotion record
- Claim statuses: `active`, `superseded`, `invalidated` — no `declared` or `reinforced` status
- `claim_lifecycle_events` tracks transitions but only knows about demotion flows

### Architectural Constraints

- **Primitive:** `ConstitutionRules` — authorizes governance refinement
- **Component being modified:** `BlueprintPromotionGate` (Operation, parent: ConstitutionRules)
- **Component being extended:** `blueprint_claims` schema (Infrastructure, parent: ConstitutionRules)
- All changes must maintain the Three-Tier chain: Artifact -> Component -> Primitive

## 4. Risks & Unknowns

- **Schema migration:** Adding `origin` column to `blueprint_claims` requires migration for existing DBs. Mitigated by `_ensure_columns` pattern already in `artifact_database.py`.
- **Promotion record dependency:** `promotion_record_id` is NOT NULL on `blueprint_claims`. Declared claims don't go through the promotion gate, so we need either a sentinel promotion record or to make the column nullable. Making it nullable is cleaner.
- **Status explosion:** Adding too many statuses (`declared`, `reinforced`, `challenged`, `amended`) could over-complicate the lifecycle. Keep initial implementation to `declared` + existing statuses. `reinforced` can be a lifecycle event annotation rather than a distinct status.
- **Backwards compatibility:** Existing claims have no `origin` — they should default to `converged` on migration.
