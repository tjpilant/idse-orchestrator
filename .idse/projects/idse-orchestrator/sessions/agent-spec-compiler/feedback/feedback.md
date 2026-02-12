# Feedback

## External / Internal Feedback
- Profiler implementation completed for phases 4-9 scope in this session.
- Existing compiler behavior was left intact; new functionality is additive under `idse profiler`.

## Risks / Issues Raised
- Current measurability and multi-objective checks are heuristics; some edge cases can produce false positives/negatives.
- `idse profiler intake` currently emits mapped JSON and does not auto-write back into `spec.md` Agent Profile block.
- Mapper output includes extended fields that are not part of the current strict `AgentProfileSpec` Pydantic model used by compiler emission.

## Actions / Follow-ups
- Action: Add configurable phrase lists/rules to reduce heuristic false positives.
  - Owner: maintainers
  - Status: open
- Action: Add optional command to patch accepted intake output into `spec.md` fenced YAML block.
  - Owner: maintainers
  - Status: open
- Action: Decide whether compiler `AgentProfileSpec` model should be extended to include profiler-produced fields.
  - Owner: maintainers
  - Status: open

## Decision Log
- Decision: Implement profiler as separate pre-compiler package (`src/idse_orchestrator/profiler/`) instead of folding into compiler package.
  - Rationale: keeps deterministic compiler stable and isolates intake/enforcement concerns.
- Decision: Return structured rejections with canonical codes plus `next_questions`.
  - Rationale: aligns with type-checker style diagnostics and supports iterative intake correction.
- Decision: Ship JSON Schema export command now (`idse profiler export-schema`).
  - Rationale: enables UI/Notion form validation without coupling to CLI runtime.
