# Intent: Blueprint Bootstrap Lifecycle

## Goal

Refactor the blueprint promotion gate and claim lifecycle to support **blueprint-as-first-pipeline** — the model where `__blueprint__` is the root pipeline execution that declares a project's founding constraints, not a retroactive distillation of feature session convergence.

## Problem / Opportunity

The current promotion gate (`BlueprintPromotionGate.evaluate_promotion`) requires:

1. **Session diversity** — evidence from at least 2 distinct sessions
2. **Stage diversity** — evidence from at least 2 distinct pipeline stages
3. **Temporal stability** — 7 days between earliest and latest evidence
4. **Feedback evidence** — at least one feedback artifact from a source session

These rules assume that claims **emerge from convergence across feature sessions over time**. This means:

- At project bootstrap, when only `__blueprint__` exists, **no claim can pass the promotion gate**
- The blueprint cannot govern feature sessions until those sessions exist and produce evidence — a circular dependency
- Founding architectural decisions (e.g., "SQLite is the authoritative backend") have no path into the claim lifecycle until after they've been implemented, which defeats the purpose of declaring them upfront

This is a bootstrapping problem. The promotion gate was designed around a harder separation model where blueprint sits above and apart from sessions. The correct model is that blueprint **is** the first pipeline execution, and its initial claims are **declarations** (axioms) rather than **convergences** (proven patterns).

## Stakeholders / Users

- **Project architects** — need to declare founding constraints at project init
- **Feature session agents** — need blueprint claims to exist as governance constraints before they start work
- **Promotion gate** — needs to distinguish between declared (bootstrap) and converged (cross-session) claims
- **New project adopters** — bootstrapping a new IDSE project is blocked without this

## Success Criteria (measurable)

- A new project can declare founding claims through its `__blueprint__` pipeline run without requiring multi-session evidence
- Declared claims enter the lifecycle with `declared` status and are immediately active for governance
- Declared claims are challengeable — feature session feedback can trigger reinforcement, amendment, or invalidation
- The existing convergence-based promotion path remains intact for cross-session claims
- All 112+ existing tests continue to pass; new tests cover the declaration lifecycle

## Constraints / Assumptions / Risks

- Must not break existing promotion/demotion workflows
- Must not change the meaning of existing claim statuses (`active`, `superseded`, `invalidated`)
- Declared claims must be distinguishable from converged claims in the DB and in file views
- The spine primitive `ConstitutionRules` authorizes this — we are refining governance, not adding new primitives
- Risk: over-engineering the lifecycle transitions — keep the initial implementation minimal

## Scope

- **In scope:** `declare_claim` method, `origin` column, CLI `blueprint declare`, lifecycle transitions for declared claims, file view updates, tests
- **Out of scope:** blueprint-specific pipeline templates, `idse init` changes, Notion sync, automated challenge detection from feedback
- **Dependencies:** `blueprint_promotion.py`, `artifact_database.py`, `cli.py`, `file_view_generator.py`

## Time / Priority

- Priority: High — blocks adoption in new projects
- Target: Current sprint
