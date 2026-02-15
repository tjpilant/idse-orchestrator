# Tasks

[P] = parallel safe

## Phase 0 — Audit existing compiler

- [x] Task 0.1 — Read and verify all 7 compiler modules (Owner: implementer) (Deps: none) (Acceptance: all modules understood, no import errors)
- [x] Task 0.2 — Run existing compiler tests, confirm 7 pass (Owner: implementer) (Deps: 0.1) (Acceptance: `pytest tests/test_compiler/ -q` → 7 passed)
- [x] Task 0.3 — Document any code-level issues beyond known gaps (Owner: implementer) (Deps: 0.1) (Acceptance: issues logged or "none found")

## Phase 1 — SQLite-backed SessionLoader

- [x] Task 1.1 — Update `SessionLoader.__init__()` to accept `backend` and `idse_root` parameters (Owner: implementer) (Deps: 0.2) (Acceptance: constructor accepts new params without breaking existing callers)
- [x] Task 1.2 — Add SQLite loading path: when `backend="sqlite"`, use `ArtifactDatabase.load_artifact(project, session_id, "spec").content` (Owner: implementer) (Deps: 1.1) (Acceptance: loads spec content from DB)
- [x] Task 1.3 — Add filesystem fallback when DB is unavailable (Owner: implementer) (Deps: 1.2) (Acceptance: graceful fallback, no crash)
- [x] Task 1.4 — Update `compile_agent_spec()` in `__init__.py` to pass backend through to `SessionLoader` (Owner: implementer) (Deps: 1.3) (Acceptance: CLI `--backend` flag works or auto-detects)
- [x] Task 1.5 — Update CLI command to wire backend parameter from global `--backend` option (Owner: implementer) (Deps: 1.4) (Acceptance: `idse compile agent-spec` respects `--backend sqlite`)

## Phase 2 — Tests and validation

- [x] Task 2.1 — [P] Add test: SQLite-backed SessionLoader loads spec content correctly (Owner: implementer) (Deps: 1.2) (Acceptance: test passes)
- [x] Task 2.2 — [P] Add test: end-to-end compilation from filled spec.md to valid YAML output (Owner: implementer) (Deps: 1.4) (Acceptance: test passes, output matches AgentProfileSpec schema)
- [x] Task 2.3 — [P] Add test: missing required fields raises ValidationError (Owner: implementer) (Deps: none) (Acceptance: test passes)
- [x] Task 2.4 — [P] Add test: blueprint + feature merge override behavior (Owner: implementer) (Deps: none) (Acceptance: feature values override blueprint, dicts merge, lists replace)
- [x] Task 2.5 — Run full test suite: existing 7 + new tests all pass (Owner: implementer) (Deps: 2.1-2.4) (Acceptance: `pytest tests/test_compiler/ -q` → 11+ passed)

## Phase 3 — Documentation and self-test

- [x] Task 3.1 — Run `idse compile agent-spec --session agent-spec-compiler --project idse-orchestrator --dry-run` to self-validate (Owner: implementer) (Deps: 2.5) (Acceptance: valid YAML output printed)
- [x] Task 3.2 — Write implementation/README.md with architecture, what was built, validation reports, component impact report (Owner: implementer) (Deps: 3.1) (Acceptance: passes validation engine checks)
- [x] Task 3.3 — Write feedback/feedback.md with lessons learned and decision log (Owner: implementer) (Deps: 3.2) (Acceptance: non-empty, no placeholders)
- [x] Task 3.4 — `idse artifact write` for implementation and feedback stages (Owner: implementer) (Deps: 3.2, 3.3) (Acceptance: DB artifacts updated)

---

## Phase 4 — Profiler Data Models & Validation (Scope Expansion 2026-02-11)

- [x] Task 4.1 — Create `src/idse_orchestrator/profiler/` package directory (Owner: implementer) (Deps: none) (Acceptance: package exists with `__init__.py`)
- [x] Task 4.2 — Implement Pydantic models in `profiler/models.py`: ObjectiveFunction, CoreTask, AuthorityBoundary, OutputContract, MissionContract, PersonaOverlay, AgentSpecProfilerDoc (Owner: implementer) (Deps: 4.1) (Acceptance: all models importable, Pydantic validation works)
- [x] Task 4.3 — Implement diagnostic models: ProfilerError, ProfilerRejection, ProfilerAcceptance (Owner: implementer) (Deps: 4.2) (Acceptance: rejection includes errors + next_questions)
- [x] Task 4.4 — Implement enforcement rules in `profiler/validate.py`: generic language detection, multi-objective detection, measurability check (Owner: implementer) (Deps: 4.2) (Acceptance: validate_profiler_doc() returns ProfilerRejection or None)
- [x] Task 4.5 — [P] Add test: valid mission contract passes validation (Owner: implementer) (Deps: 4.4) (Acceptance: test passes)
- [x] Task 4.6 — [P] Add test: generic objective rejected with error code (Owner: implementer) (Deps: 4.4) (Acceptance: test passes)
- [x] Task 4.7 — [P] Add test: multi-objective rejected with error code (Owner: implementer) (Deps: 4.4) (Acceptance: test passes)
- [x] Task 4.8 — [P] Add test: non-measurable metric rejected (Owner: implementer) (Deps: 4.4) (Acceptance: test passes)
- [x] Task 4.9 — [P] Add test: missing constraints/exclusions/failures rejected (Owner: implementer) (Deps: 4.4) (Acceptance: test passes)

## Phase 5 — Profiler Mapper

- [x] Task 5.1 — Implement `profiler/map_to_agent_profile_spec.py` with `to_agent_profile_spec()` function (Owner: implementer) (Deps: 4.2) (Acceptance: deterministic mapping from ProfilerDoc to AgentProfileSpec dict)
- [x] Task 5.2 — [P] Add test: full mission contract maps to complete AgentProfileSpec (Owner: implementer) (Deps: 5.1) (Acceptance: test passes)
- [x] Task 5.3 — [P] Add test: persona overlay maps correctly (Owner: implementer) (Deps: 5.1) (Acceptance: test passes)

## Phase 5.5 — Profiler Document Generator

- [x] Task 5.5.1 — Create `profiler/generate_spec_document.py` module (Owner: implementer) (Deps: 4.2) (Acceptance: module created with imports)
- [x] Task 5.5.2 — Implement `generate_intent_section(doc)` — produces ## Intent prose from objective_function + success_metric (Owner: implementer) (Deps: 5.5.1) (Acceptance: function returns non-empty markdown string with Goal, Problem, Stakeholders, Success Criteria subsections)
- [x] Task 5.5.3 — Implement `generate_context_section(doc)` — produces ## Context prose from authority_boundary + constraints (Owner: implementer) (Deps: 5.5.1) (Acceptance: function returns prose narrative explaining boundaries, not just bullet lists)
- [x] Task 5.5.4 — Implement `generate_tasks_section(doc)` — produces ## Tasks list from core_tasks (Owner: implementer) (Deps: 5.5.1) (Acceptance: function returns markdown list with task + method pairs)
- [x] Task 5.5.5 — Implement `generate_specification_section(doc)` — produces ## Specification with FR-N, AC-N requirements (Owner: implementer) (Deps: 5.5.1) (Acceptance: function returns structured requirements with numbered FR-1..FR-N and AC-1..AC-N)
- [x] Task 5.5.6 — Implement `generate_agent_profile_yaml(doc)` — produces ## Agent Profile YAML block (Owner: implementer) (Deps: 5.1, 5.5.1) (Acceptance: uses to_agent_profile_spec() + YAML serialization)
- [x] Task 5.5.7 — Implement `generate_complete_spec_md(doc)` orchestrator function (Owner: implementer) (Deps: 5.5.2-5.5.6) (Acceptance: assembles all sections into complete spec.md string)
- [x] Task 5.5.8 — [P] Add test: generated ## Intent includes all required subsections (Owner: implementer) (Deps: 5.5.2) (Acceptance: test passes)
- [x] Task 5.5.9 — [P] Add test: generated ## Specification includes numbered FR-N and AC-N (Owner: implementer) (Deps: 5.5.5) (Acceptance: test passes)
- [x] Task 5.5.10 — [P] Add test: generated ## Agent Profile YAML validates against AgentProfileSpec schema (Owner: implementer) (Deps: 5.5.6) (Acceptance: test passes)
- [x] Task 5.5.11 — [P] Add test: complete spec.md can be parsed by existing compile_agent_spec() (Owner: implementer) (Deps: 5.5.7) (Acceptance: test passes)
- [x] Task 5.5.12 — [P] Add test: generated prose reads like HR job description (not robotic) (Owner: implementer) (Deps: 5.5.7) (Acceptance: manual review confirms prose quality)

## Phase 6 — Profiler CLI 3-Phase Pipeline

- [x] Task 6.1 — Implement `profiler/cli.py` Phase 1: interactive 20-question intake (Owner: implementer) (Deps: 4.2) (Acceptance: CLI prompts all questions, collects answers into AgentSpecProfilerDoc)
- [x] Task 6.2 — Implement Phase 2: validation with ProfilerRejection + next_questions (Owner: implementer) (Deps: 4.4, 6.1) (Acceptance: CLI validates, shows errors, allows retry on rejection)
- [x] Task 6.3 — Implement Phase 3: document generation integration (Owner: implementer) (Deps: 5.5.7, 6.2) (Acceptance: CLI calls generate_complete_spec_md() and writes to file)
- [x] Task 6.4 — Wire `idse profiler intake` command in main CLI (Owner: implementer) (Deps: 6.3) (Acceptance: command available in `idse --help`)
- [x] Task 6.5 — [P] Add test: CLI completes full 3-phase pipeline without crashes (Owner: implementer) (Deps: 6.3) (Acceptance: test passes)
- [x] Task 6.6 — [P] Add test: valid answers produce complete spec.md file (Owner: implementer) (Deps: 6.3) (Acceptance: test passes, spec.md contains all sections)
- [x] Task 6.7 — [P] Add test: invalid answers show ProfilerRejection with next_questions (Owner: implementer) (Deps: 6.2) (Acceptance: test passes)

## Phase 7 — Profiler Integration with Compiler

- [x] Task 7.1 — Document complete 3-phase flow in profiler README (Owner: implementer) (Deps: 6.4) (Acceptance: flow documented with Intake → Validation → Document Generation → Compilation sections)
- [x] Task 7.2 — Add end-to-end test: profiler intake → spec.md → compile_agent_spec → .profile.yaml (Owner: implementer) (Deps: 6.4, 2.5) (Acceptance: test passes, .profile.yaml validates)
- [x] Task 7.3 — Run manual dogfood: `idse profiler intake --agent-name test-agent` produces complete spec.md (Owner: implementer) (Deps: 6.4) (Acceptance: spec.md generated with all sections)
- [x] Task 7.4 — Verify generated spec.md can be compiled without edits (Owner: implementer) (Deps: 7.3) (Acceptance: `idse compile agent-spec --session test-agent` succeeds)

## Phase 8 — JSON Schema Export (Optional)

- [x] Task 8.1 — Implement `profiler/schema.py` with JSON Schema export (Owner: implementer) (Deps: 4.2) (Acceptance: generates valid JSON Schema)
- [x] Task 8.2 — Add `idse profiler export-schema` CLI command (Owner: implementer) (Deps: 8.1) (Acceptance: command writes schema to file)

## Phase 9 — Profiler Documentation & Self-Test

- [x] Task 9.1 — Document Profiler architecture in implementation/README.md (Owner: implementer) (Deps: 7.2) (Acceptance: architecture, 3-phase pipeline, models, validation rules, document generation documented)
- [x] Task 9.2 — Create 2 example spec.md files in profiler/examples/ (Owner: implementer) (Deps: 5.5.7) (Acceptance: restaurant_blog_writer.spec.md and data_scientist.spec.md exist, both generated from Profiler)
- [x] Task 9.3 — Run Profiler self-test: generate spec.md for agent-spec-compiler session (Owner: implementer) (Deps: 6.4) (Acceptance: complete spec.md generated)
- [x] Task 9.4 — Update feedback/feedback.md with Profiler lessons learned (Owner: implementer) (Deps: 9.3) (Acceptance: non-empty, documents document generation challenges, prose quality insights)

## Phase 10 — Production Hardening (Adversarial Testing & Drift Detection)

- [x] Task 10.1 — Add `schema_version: str = "1.0"` field to `AgentSpecProfilerDoc` model (Owner: implementer) (Deps: 4.2) (Acceptance: field added, default value set)
- [x] Task 10.2 — Add `profiler_hash: str` computation in `generate_agent_profile_yaml()` — SHA256 of normalized ProfilerDoc (Owner: implementer) (Deps: 5.5.6, 10.1) (Acceptance: hash embedded in generated YAML as `# profiler_hash: <sha256>` comment)
- [x] Task 10.3 — Add hash validation in `SessionLoader.load_spec()` — warn if hash missing or mismatched (Owner: implementer) (Deps: 1.2, 10.2) (Acceptance: logs warning when manual edits detected)
- [x] Task 10.4 — Add 4 new error codes to `profiler/error_codes.py`: E1008 (non_actionable_method), E1017 (scope_contradiction), W2002 (success_metric_not_locally_verifiable), E1018 (output_contract_incoherent) (Owner: implementer) (Deps: 4.4) (Acceptance: error codes defined with numeric IDs, messages, next_questions, severity)
- [x] Task 10.5 — Implement `_detect_scope_contradictions()` in `profiler/validate.py` — cross-check explicit_exclusions vs core_tasks vs output_contract (Owner: implementer) (Deps: 10.4) (Acceptance: returns ProfilerError if contradictions found)
- [x] Task 10.6 — Implement `_detect_unverifiable_metrics()` in `profiler/validate.py` — check if success_metric requires tools not in authority_boundary.may (Owner: implementer) (Deps: 10.4) (Acceptance: returns ProfilerWarning if metric not locally verifiable)
- [x] Task 10.7 — Implement `_detect_output_contract_incoherence()` in `profiler/validate.py` — check format_type vs validation_rules consistency (Owner: implementer) (Deps: 10.4) (Acceptance: returns ProfilerError if format="json" but validation_rules mention "markdown sections")
- [x] Task 10.8 — Implement `_detect_non_actionable_methods()` in `profiler/validate.py` — flag methods with generic platitudes (Owner: implementer) (Deps: 10.4) (Acceptance: returns ProfilerError if method is "best practices", "leverage AI", etc.)
- [x] Task 10.9 — [P] Add adversarial test: Vague Multi-Tasker (expect E1001, E1002, E1004) (Owner: implementer) (Deps: 10.4-10.8) (Acceptance: test passes, correct error codes returned)
- [x] Task 10.10 — [P] Add adversarial test: Over-Scoped Agent with 9 tasks (expect E1006) (Owner: implementer) (Deps: 10.4) (Acceptance: test passes)
- [x] Task 10.11 — [P] Add adversarial test: Authority Hole (missing may_not, expect E1010) (Owner: implementer) (Deps: 10.4) (Acceptance: test passes)
- [x] Task 10.12 — [P] Add adversarial test: Valid Restaurant Blogger (golden path, expect acceptance) (Owner: implementer) (Deps: 10.4-10.8) (Acceptance: test passes, generates complete spec.md)
- [x] Task 10.13 — [P] Add adversarial test: Contradiction Spec Attack (exclusions contradict tasks, expect E1017) (Owner: implementer) (Deps: 10.5) (Acceptance: test passes)
- [x] Task 10.14 — [P] Add adversarial test: Unverifiable Success Metric (metric needs tools agent doesn't have, expect W2002) (Owner: implementer) (Deps: 10.6) (Acceptance: test passes, warning issued)
- [x] Task 10.15 — [P] Add adversarial test: Output Contract Mismatch (json format with markdown validation rules, expect E1018) (Owner: implementer) (Deps: 10.7) (Acceptance: test passes)
- [x] Task 10.16 — Document schema versioning and migration strategy in profiler README (Owner: implementer) (Deps: 10.1) (Acceptance: README includes v1.0 → v2.0 migration path)
- [x] Task 10.17 — Document hash-based drift detection workflow in profiler README (Owner: implementer) (Deps: 10.2-10.3) (Acceptance: README explains when/why hash warnings appear)
- [x] Task 10.18 — Run full adversarial test suite: all 10 tests pass (Owner: implementer) (Deps: 10.9-10.15) (Acceptance: `pytest tests/test_profiler/ -k adversarial` → 10 passed)

## Phase 10.5 — Profiler UX Enhancement (JSON I/O + CLI Refactoring)

- [x] Task 10.5.1 — Add `save_profiler_answers_to_json()` function in `profiler/cli.py` (Owner: implementer) (Deps: none) (Acceptance: saves collected answers dict to JSON file with sorted keys)
- [x] Task 10.5.2 — Add `load_profiler_answers_from_json()` function in `profiler/cli.py` (Owner: implementer) (Deps: none) (Acceptance: loads JSON, validates schema, returns answers dict)
- [x] Task 10.5.3 — Add `--save-answers` flag to `profiler intake` command (Owner: implementer) (Deps: 10.5.1) (Acceptance: CLI saves collected answers to specified JSON path before validation)
- [x] Task 10.5.4 — Add `--from-json` flag to `profiler intake` command (Owner: implementer) (Deps: 10.5.2) (Acceptance: CLI skips interactive prompts, loads answers from JSON, validates and generates spec.md)
- [x] Task 10.5.5 — [P] Add test: `--save-answers` creates valid JSON file (Owner: implementer) (Deps: 10.5.3) (Acceptance: test passes, JSON contains all 20 answers)
- [x] Task 10.5.6 — [P] Add test: `--from-json` loads and validates JSON correctly (Owner: implementer) (Deps: 10.5.4) (Acceptance: test passes, same result as interactive mode)
- [x] Task 10.5.7 — [P] Add test: edit-retry workflow (save → edit JSON → reload → validate) (Owner: implementer) (Deps: 10.5.3-10.5.4) (Acceptance: test passes, edited answer triggers validation correctly)
- [x] Task 10.5.8 — Create `profiler/commands.py` module (Owner: implementer) (Deps: none) (Acceptance: module exists with imports)
- [x] Task 10.5.9 — Move profiler Click command group to `profiler/commands.py` (Owner: implementer) (Deps: 10.5.8) (Acceptance: `profiler_intake_cmd` and `profiler_export_schema_cmd` moved from `cli.py` to `profiler/commands.py`)
- [x] Task 10.5.10 — Update main `cli.py` to import and register profiler command group from `profiler/commands.py` (Owner: implementer) (Deps: 10.5.9) (Acceptance: `idse profiler` commands still work, main CLI under 1800 lines)
- [x] Task 10.5.11 — Update profiler README with JSON I/O workflow examples (Owner: implementer) (Deps: 10.5.3-10.5.4) (Acceptance: README documents `--save-answers` and `--from-json` usage with example edit-retry workflow)
- [x] Task 10.5.12 — Run full profiler test suite with new JSON I/O tests (Owner: implementer) (Deps: 10.5.5-10.5.7) (Acceptance: all profiler tests pass including new JSON I/O tests)
