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
