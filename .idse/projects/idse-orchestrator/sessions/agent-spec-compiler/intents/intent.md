# Intent

## Goal
Audit, validate, and document the existing DocToAgentProfileSpec compiler (`compiler/` package) as a first-class IDSE primitive. Identify gaps between what was built (Feb 2, 2026 extraction) and what the blueprint spec requires, then close those gaps.

## Problem / Opportunity
- The compiler exists (`src/idse_orchestrator/compiler/`) with 7 modules, 7 passing tests, and a wired CLI command (`idse compile agent-spec`).
- It was built during initial repo extraction (commit `fa9a3d3`) but has never been exercised against a real project with filled-out Agent Profile YAML.
- The blueprint plan (Phase 5) exit criteria state: "PromptBraining / Artifact Core can consume that spec without special casing." This has not been validated.
- The `SessionLoader` reads from filesystem only — it does not use the SQLite backend (source of truth).
- The `AgentProfileSpec` Pydantic model may need alignment with what PromptBraining actually expects to consume.

## Stakeholders / Users
- IDSE developers authoring `spec.md` with `## Agent Profile` YAML blocks
- PromptBraining runtime (downstream consumer of compiled `.profile.yaml`)
- CI/CD pipelines that may run `idse compile agent-spec` as a build step

## Success Criteria (measurable)
- Compiler reads from SQLite backend (not just filesystem)
- End-to-end test: filled `spec.md` → `idse compile agent-spec` → valid `.profile.yaml`
- `AgentProfileSpec` schema documented and versioned
- Blueprint exit criteria met: output consumable by downstream runtimes without special casing

## Constraints / Assumptions / Risks
- No runtime LLM calls — compiler is deterministic, design-time only
- No dependencies on PromptBraining internals — compiler outputs a spec file, does not import runtime modules
- Risk: `AgentProfileSpec` schema may drift if PromptBraining evolves independently — need versioning strategy

## Scope
- In scope: Audit existing compiler, fix SessionLoader to use SQLite, validate end-to-end, document schema and mapping rules
- Out of scope: PromptBraining runtime integration, ZPromptCompiler, AgentRuntime
- Dependencies: Existing `compiler/` package, `ArtifactDatabase` for SQLite reads

## Time / Priority
- Priority: Medium — bridge to PromptBraining project
- No hard deadline
