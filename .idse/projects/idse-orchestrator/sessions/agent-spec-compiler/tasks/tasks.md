# Tasks

[P] = parallel safe

## Phase 0 — Audit existing compiler

- [ ] Task 0.1 — Read and verify all 7 compiler modules (Owner: implementer) (Deps: none) (Acceptance: all modules understood, no import errors)
- [ ] Task 0.2 — Run existing compiler tests, confirm 7 pass (Owner: implementer) (Deps: 0.1) (Acceptance: `pytest tests/test_compiler/ -q` → 7 passed)
- [ ] Task 0.3 — Document any code-level issues beyond known gaps (Owner: implementer) (Deps: 0.1) (Acceptance: issues logged or "none found")

## Phase 1 — SQLite-backed SessionLoader

- [ ] Task 1.1 — Update `SessionLoader.__init__()` to accept `backend` and `idse_root` parameters (Owner: implementer) (Deps: 0.2) (Acceptance: constructor accepts new params without breaking existing callers)
- [ ] Task 1.2 — Add SQLite loading path: when `backend="sqlite"`, use `ArtifactDatabase.load_artifact(project, session_id, "spec").content` (Owner: implementer) (Deps: 1.1) (Acceptance: loads spec content from DB)
- [ ] Task 1.3 — Add filesystem fallback when DB is unavailable (Owner: implementer) (Deps: 1.2) (Acceptance: graceful fallback, no crash)
- [ ] Task 1.4 — Update `compile_agent_spec()` in `__init__.py` to pass backend through to `SessionLoader` (Owner: implementer) (Deps: 1.3) (Acceptance: CLI `--backend` flag works or auto-detects)
- [ ] Task 1.5 — Update CLI command to wire backend parameter from global `--backend` option (Owner: implementer) (Deps: 1.4) (Acceptance: `idse compile agent-spec` respects `--backend sqlite`)

## Phase 2 — Tests and validation

- [ ] Task 2.1 — [P] Add test: SQLite-backed SessionLoader loads spec content correctly (Owner: implementer) (Deps: 1.2) (Acceptance: test passes)
- [ ] Task 2.2 — [P] Add test: end-to-end compilation from filled spec.md to valid YAML output (Owner: implementer) (Deps: 1.4) (Acceptance: test passes, output matches AgentProfileSpec schema)
- [ ] Task 2.3 — [P] Add test: missing required fields raises ValidationError (Owner: implementer) (Deps: none) (Acceptance: test passes)
- [ ] Task 2.4 — [P] Add test: blueprint + feature merge override behavior (Owner: implementer) (Deps: none) (Acceptance: feature values override blueprint, dicts merge, lists replace)
- [ ] Task 2.5 — Run full test suite: existing 7 + new tests all pass (Owner: implementer) (Deps: 2.1-2.4) (Acceptance: `pytest tests/test_compiler/ -q` → 11+ passed)

## Phase 3 — Documentation and self-test

- [ ] Task 3.1 — Run `idse compile agent-spec --session agent-spec-compiler --project idse-orchestrator --dry-run` to self-validate (Owner: implementer) (Deps: 2.5) (Acceptance: valid YAML output printed)
- [ ] Task 3.2 — Write implementation/README.md with architecture, what was built, validation reports, component impact report (Owner: implementer) (Deps: 3.1) (Acceptance: passes validation engine checks)
- [ ] Task 3.3 — Write feedback/feedback.md with lessons learned and decision log (Owner: implementer) (Deps: 3.2) (Acceptance: non-empty, no placeholders)
- [ ] Task 3.4 — `idse artifact write` for implementation and feedback stages (Owner: implementer) (Deps: 3.2, 3.3) (Acceptance: DB artifacts updated)

---

## Phase 4 — Profiler Data Models & Validation (Scope Expansion 2026-02-11)

- [ ] Task 4.1 — Create `src/idse_orchestrator/profiler/` package directory (Owner: implementer) (Deps: none) (Acceptance: package exists with `__init__.py`)
- [ ] Task 4.2 — Implement Pydantic models in `profiler/models.py`: ObjectiveFunction, CoreTask, AuthorityBoundary, OutputContract, MissionContract, PersonaOverlay, AgentSpecProfilerDoc (Owner: implementer) (Deps: 4.1) (Acceptance: all models importable, Pydantic validation works)
- [ ] Task 4.3 — Implement diagnostic models: ProfilerError, ProfilerRejection, ProfilerAcceptance (Owner: implementer) (Deps: 4.2) (Acceptance: rejection includes errors + next_questions)
- [ ] Task 4.4 — Implement enforcement rules in `profiler/validate.py`: generic language detection, multi-objective detection, measurability check (Owner: implementer) (Deps: 4.2) (Acceptance: validate_profiler_doc() returns ProfilerRejection or None)
- [ ] Task 4.5 — [P] Add test: valid mission contract passes validation (Owner: implementer) (Deps: 4.4) (Acceptance: test passes)
- [ ] Task 4.6 — [P] Add test: generic objective rejected with error code (Owner: implementer) (Deps: 4.4) (Acceptance: test passes)
- [ ] Task 4.7 — [P] Add test: multi-objective rejected with error code (Owner: implementer) (Deps: 4.4) (Acceptance: test passes)
- [ ] Task 4.8 — [P] Add test: non-measurable metric rejected (Owner: implementer) (Deps: 4.4) (Acceptance: test passes)
- [ ] Task 4.9 — [P] Add test: missing constraints/exclusions/failures rejected (Owner: implementer) (Deps: 4.4) (Acceptance: test passes)

## Phase 5 — Profiler Mapper

- [ ] Task 5.1 — Implement `profiler/map_to_agent_profile_spec.py` with `to_agent_profile_spec()` function (Owner: implementer) (Deps: 4.2) (Acceptance: deterministic mapping from ProfilerDoc to AgentProfileSpec dict)
- [ ] Task 5.2 — [P] Add test: full mission contract maps to complete AgentProfileSpec (Owner: implementer) (Deps: 5.1) (Acceptance: test passes)
- [ ] Task 5.3 — [P] Add test: persona overlay maps correctly (Owner: implementer) (Deps: 5.1) (Acceptance: test passes)

## Phase 6 — Profiler CLI Intake

- [ ] Task 6.1 — Implement `profiler/cli.py` with interactive 20-question intake flow (Owner: implementer) (Deps: 4.2, 4.4, 5.1) (Acceptance: CLI prompts all questions, collects answers)
- [ ] Task 6.2 — Wire `idse profiler intake` command in main CLI (Owner: implementer) (Deps: 6.1) (Acceptance: command available in `idse --help`)
- [ ] Task 6.3 — [P] Add test: CLI completes intake without crashes (Owner: implementer) (Deps: 6.1) (Acceptance: test passes)
- [ ] Task 6.4 — [P] Add test: valid answers produce AgentProfileSpec JSON (Owner: implementer) (Deps: 6.1) (Acceptance: test passes)
- [ ] Task 6.5 — [P] Add test: invalid answers show ProfilerRejection with next_questions (Owner: implementer) (Deps: 6.1) (Acceptance: test passes)

## Phase 7 — Profiler Integration with Compiler

- [ ] Task 7.1 — Document integration flow in profiler README (Owner: implementer) (Deps: 6.2) (Acceptance: flow documented)
- [ ] Task 7.2 — Add end-to-end test: profiler intake → compiler → .profile.yaml (Owner: implementer) (Deps: 6.2, 2.5) (Acceptance: test passes)
- [ ] Task 7.3 — Run manual dogfood: `idse profiler intake` for agent-spec-compiler session (Owner: implementer) (Deps: 6.2) (Acceptance: valid AgentProfileSpec JSON produced)

## Phase 8 — JSON Schema Export (Optional)

- [ ] Task 8.1 — Implement `profiler/schema.py` with JSON Schema export (Owner: implementer) (Deps: 4.2) (Acceptance: generates valid JSON Schema)
- [ ] Task 8.2 — Add `idse profiler export-schema` CLI command (Owner: implementer) (Deps: 8.1) (Acceptance: command writes schema to file)

## Phase 9 — Profiler Documentation & Self-Test

- [ ] Task 9.1 — Document Profiler architecture in implementation/README.md (Owner: implementer) (Deps: 7.2) (Acceptance: architecture, models, validation rules documented)
- [ ] Task 9.2 — Create 2 example .profiler.json files in profiler/examples/ (Owner: implementer) (Deps: 5.1) (Acceptance: examples exist and validate)
- [ ] Task 9.3 — Run Profiler self-test with this session's mission contract (Owner: implementer) (Deps: 6.2) (Acceptance: valid AgentProfileSpec emitted)
- [ ] Task 9.4 — Update feedback/feedback.md with Profiler lessons learned (Owner: implementer) (Deps: 9.3) (Acceptance: non-empty, no placeholders)
