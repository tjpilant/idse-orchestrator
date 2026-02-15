# Feedback

## External / Internal Feedback
- All 11 phases (0-10) of the agent-spec-compiler plan are implemented and tested.
- Full regression suite: **174 tests pass, 0 failures**.
- Existing compiler behavior was left intact; new functionality is additive under `idse profiler`.
- `--spec-out` option now resolves the prior gap: profiler intake can write spec.md directly.
- Self-test confirmed: `idse compile agent-spec --session agent-spec-compiler --dry-run` produces valid YAML.

## Risks / Issues Raised
- Current measurability and multi-objective checks are heuristics; some edge cases can produce false positives/negatives.
- Pydantic schema constraints enforce before heuristic validation. Error codes E1006 (too many tasks) and E1010 (missing may_not) are enforced by Pydantic `max_length` and `min_length`, not by `validate_profiler_doc()`. Downstream consumers expecting E1006/E1010 from the validator will get `PydanticValidationError` instead.
- Hash-based drift detection currently only logs warnings (debug level). No enforcement (rejection) mode exists yet.
- `schema_version` is set to `"1.0"` with no migration path for future schema changes.
- **CRITICAL UX GAP**: PFR-2 ("Profiler MUST save partial progress") is incomplete. When validation fails (e.g., E1002 multi_objective_agent), users must restart the entire 20-question intake from scratch. No `--from-json` or `--save-answers` flags exist to enable answer editing and re-validation. This forces users to re-answer all 20 questions even when only 1 answer needs correction. Discovered during manual testing when transformation summary validation failed after completing all 20 questions.

## Actions / Follow-ups
- **Action: Implement `--from-json` and `--save-answers` flags for profiler intake to enable answer editing after validation failures.**
  - Owner: implementer (Phase 10.5)
  - Status: **URGENT** — blocks usable UX for iterative refinement
  - Details: Save collected answers as JSON before validation, allow loading from JSON to skip re-prompting, enable edit-retry workflow
- Action: Refactor profiler CLI commands to separate module (`profiler/commands.py`) to prevent main CLI bloat.
  - Owner: implementer (Phase 10.5)
  - Status: open
  - Details: Extract profiler command group from `cli.py` into `profiler/commands.py`, keep main CLI under 2000 lines
- Action: Add configurable phrase lists/rules to reduce heuristic false positives.
  - Owner: maintainers
  - Status: open
- Action: Decide whether E1006/E1010 should be duplicated in `validate_profiler_doc()` for consumers that bypass Pydantic construction.
  - Owner: maintainers
  - Status: open
- Action: Implement enforcement mode for profiler_hash drift (reject compilation when hash mismatches, not just warn).
  - Owner: maintainers
  - Status: open
- Action: Design schema_version migration strategy before releasing v1.1.
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
- Decision: Adversarial tests 2 and 6 test Pydantic guard instead of heuristic validator for over-scoped/excessive tasks.
  - Rationale: Pydantic fires at construction time; the heuristic layer never sees invalid data.
- Decision: Document generator produces prose from structured fields via deterministic templates, not LLM inference.
  - Rationale: reproducibility and offline operation are primary constraints.
- Decision: profiler_hash uses SHA256 of JSON-serialized ProfilerDoc (sorted keys, compact separators).
  - Rationale: deterministic, language-agnostic, and collision-resistant.

## Lessons Learned
- Pydantic v2 schema constraints create a "two-layer" validation boundary. Design error codes knowing which layer catches which violation.
- Document generation from structured data requires careful prose quality. Template-based generation produces acceptable but formulaic output.
- End-to-end integration tests (profiler → spec.md → compiler → .profile.yaml) are the most valuable tests in the suite — they catch interface mismatches between independently developed components.
- Stable numeric error code IDs (E1000-E1018, W2001-W2002) enable future tooling (IDE integrations, CI scripts) without string parsing.
