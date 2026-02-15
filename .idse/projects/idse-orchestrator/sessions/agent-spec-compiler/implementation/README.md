# Implementation: idse-orchestrator

Session: agent-spec-compiler  
Stack: python  
Updated: 2026-02-12

## Architecture

The compiler pipeline remains `load -> parse -> merge -> validate -> emit`. This implementation adds:

1. **SQLite-backed SessionLoader** — reads `spec.md` from SQLite via `ArtifactDatabase`, falls back to filesystem
2. **Profiler pre-compiler layer** — 3-phase pipeline: `intake -> validation -> document generation`
3. **Document Generator** — transforms validated `AgentSpecProfilerDoc` into complete IDSE `spec.md`
4. **Production Hardening** — hash-based drift detection, schema versioning, adversarial test suite

### Complete Pipeline Flow

```
idse profiler intake --spec-out <path>
  │
  ├─ Phase 1: 20-question interactive intake
  ├─ Phase 2: Validation ("Psychoanalysis")
  │  ├─ Pydantic schema validation
  │  └─ 22 canonical error codes (E1000-E1018, W2001-W2002)
  └─ Phase 3: Document Generation
     ├─ ## Intent (prose from objective_function)
     ├─ ## Context (prose from authority_boundary + constraints)
     ├─ ## Tasks (list from core_tasks with methods)
     ├─ ## Specification (FR-N, AC-N requirements)
     └─ ## Agent Profile (YAML block with profiler_hash)
  │
  ▼
idse compile agent-spec --session <id> --project <name>
  │
  ├─ SessionLoader reads spec.md from SQLite (primary) or filesystem (fallback)
  ├─ Hash validation (warns on missing/mismatched profiler_hash)
  ├─ parse_agent_profile() extracts ## Agent Profile YAML
  ├─ merge_profiles() (blueprint + feature deep merge)
  ├─ AgentProfileSpec Pydantic validation
  └─ emit_profile() → <session>.profile.yaml
```

## What Was Built

### Phase 0-3: Compiler Hardening
1. **SessionLoader SQLite backend** — reads from `ArtifactDatabase.load_artifact()`, falls back to filesystem
2. **Hash-based drift detection** — `SessionLoader.load_spec()` checks for `# profiler_hash:` comments, logs warnings when missing
3. **Self-test** — `idse compile agent-spec --session agent-spec-compiler --project idse-orchestrator --dry-run` produces valid YAML

### Phase 4-5: Profiler Data Models & Mapper
4. **Profiler package** (`src/idse_orchestrator/profiler/`) with 7 modules:
   - `models.py` — ObjectiveFunction, CoreTask, AuthorityBoundary, OutputContract, MissionContract, PersonaOverlay, AgentSpecProfilerDoc (with `schema_version: str = "1.0"`)
   - `error_codes.py` — 22 canonical error codes with stable numeric IDs (E1000-E1018, W2001-W2002)
   - `validate.py` — Enforcement rules engine with 8 detection functions
   - `map_to_agent_profile_spec.py` — Deterministic mapper (zero inference)
   - `cli.py` — Interactive 20-question intake + 3-phase pipeline
   - `schema.py` — JSON Schema export from Pydantic models
   - `generate_spec_document.py` — Complete spec.md document generator

### Phase 5.5: Document Generator
5. **Document generator** (`generate_spec_document.py`) with 6 public functions:
   - `generate_intent_section()` — Goal, Problem/Opportunity, Stakeholders, Success Criteria
   - `generate_context_section()` — Authority boundaries, constraints, exclusions narrative
   - `generate_tasks_section()` — Core tasks with methods
   - `generate_specification_section()` — FR-N, NFR-N, AC-N numbered requirements
   - `generate_agent_profile_yaml()` — YAML block with `# profiler_hash: <sha256>`
   - `generate_complete_spec_md()` — Orchestrates all generators

### Phase 6: CLI Integration
6. **CLI `--spec-out` option** — `idse profiler intake --spec-out <path>` writes generated spec.md directly

### Phase 10: Production Hardening
7. **Schema versioning** — `AgentSpecProfilerDoc.schema_version` field (default `"1.0"`)
8. **Profiler hash** — SHA256 of normalized ProfilerDoc embedded as `# profiler_hash:` comment
9. **4 new validation functions**:
   - `_detect_non_actionable_methods()` — E1008 (platitude methods)
   - `_detect_scope_contradictions()` — E1017 (exclusions contradict tasks)
   - `_detect_unverifiable_metrics()` — W2002 (metric needs unavailable tools)
   - `_detect_output_contract_incoherence()` — E1018 (format vs validation mismatch)
10. **10-test adversarial suite** — all pass with correct error codes

### Examples
11. **2 generated spec.md examples**:
    - `profiler/examples/restaurant_blog_writer.spec.md`
    - `profiler/examples/data_scientist.spec.md`

## Validation Reports

- `pytest tests/ -v` → **174 passed** (0 failures)
- Compiler tests: 12 passed (SQLite loading, e2e, validation, merge)
- Profiler tests: 29 passed (validation, mapper, CLI, doc generator, integration, adversarial)
- All existing project tests: 133 passed (no regressions)
- Self-test: `idse compile agent-spec --session agent-spec-compiler --dry-run` → valid YAML

## Deviations from Plan

- No architectural deviations
- Test 2 (Over-Scoped Agent) uses Pydantic guard instead of `validate_profiler_doc()` for E1006, since Pydantic's `max_length=8` fires before the heuristic validator
- Test 6 (Excessive Tasks) tests Pydantic rejection directly for the same reason

## Component Declarations

| Component | Action | Type | Parent Primitive |
|---|---|---|---|
| `SessionLoader` (`compiler/loader.py`) | Modified | Infrastructure | `DocToAgentProfileSpecCompiler` |
| `ProfilerModels` (`profiler/models.py`) | Created | Operation | `DocToAgentProfileSpecCompiler` |
| `ProfilerErrorCodes` (`profiler/error_codes.py`) | Created | Operation | `DocToAgentProfileSpecCompiler` |
| `ProfilerValidationEngine` (`profiler/validate.py`) | Created | Operation | `DocToAgentProfileSpecCompiler` |
| `ProfilerMapper` (`profiler/map_to_agent_profile_spec.py`) | Created | Operation | `DocToAgentProfileSpecCompiler` |
| `ProfilerDocGenerator` (`profiler/generate_spec_document.py`) | Created | Projection | `DocToAgentProfileSpecCompiler` |
| `ProfilerSchemaExport` (`profiler/schema.py`) | Created | Infrastructure | `DocToAgentProfileSpecCompiler` |
| `ProfilerIntakeCLI` (`profiler/cli.py`) | Created | Routing | `CLIInterface` |
| `CLI profiler commands` (`cli.py`) | Modified | Routing | `CLIInterface` |
| `Adversarial tests` (`test_profiler/test_adversarial.py`) | Created | Artifact | `DocToAgentProfileSpecCompiler` |
| `DocGen tests` (`test_profiler/test_generate_spec_document.py`) | Created | Artifact | `DocToAgentProfileSpecCompiler` |

## Error Code Reference

| Numeric ID | Code | Severity | Description |
|---|---|---|---|
| E1000 | `missing_required_field` | error | Required field is empty or null |
| E1001 | `generic_objective_function` | error | Objective uses generic language |
| E1002 | `multi_objective_agent` | error | Multiple primary transformations |
| E1003 | `missing_success_metric` | error | No measurable success criterion |
| E1004 | `non_measurable_success_metric` | error | No numbers/percentages/time units |
| E1005 | `missing_explicit_exclusions` | error | No explicit exclusions defined |
| E1006 | `too_many_core_tasks` | error | More than 8 core tasks |
| E1007 | `missing_task` | error | Core task description is empty |
| E1008 | `non_actionable_method` | error | Method is platitude |
| E1009 | `missing_authority_boundary` | error | Authority boundary not defined |
| E1010 | `missing_may_not` | error | Missing explicit prohibitions |
| E1011 | `missing_constraints` | error | No constraints defined |
| E1012 | `missing_failure_conditions` | error | No failure conditions defined |
| E1013 | `missing_output_contract` | error | Output contract not specified |
| E1014 | `invalid_format_type` | error | format_type not in allowed values |
| E1015 | `missing_required_sections` | error | Required sections missing for narrative/hybrid |
| E1016 | `missing_validation_rules` | error | No validation rules defined |
| E1017 | `scope_contradiction` | error | Exclusions contradict core_tasks |
| E1018 | `output_contract_incoherent` | error | format_type conflicts with validation_rules |
| W2001 | `persona_leak_into_mission` | warning | Persona preferences in mission fields |
| W2002 | `success_metric_not_locally_verifiable` | warning | Metric needs unavailable tools |

## Files Touched

### New Files
- `src/idse_orchestrator/profiler/generate_spec_document.py`
- `src/idse_orchestrator/profiler/examples/restaurant_blog_writer.spec.md`
- `src/idse_orchestrator/profiler/examples/data_scientist.spec.md`
- `tests/test_profiler/test_generate_spec_document.py`
- `tests/test_profiler/test_adversarial.py`

### Modified Files
- `src/idse_orchestrator/compiler/loader.py` — Added hash validation, logging
- `src/idse_orchestrator/profiler/__init__.py` — Added `generate_complete_spec_md` export
- `src/idse_orchestrator/profiler/error_codes.py` — Added 4 new codes, numeric IDs
- `src/idse_orchestrator/profiler/models.py` — Added `schema_version`, `severity` field
- `src/idse_orchestrator/profiler/validate.py` — Added 4 new detection functions
- `src/idse_orchestrator/cli.py` — Added `--spec-out` option to intake command
- `tests/test_profiler/test_cli_profiler.py` — Added spec-out test
- `tests/test_profiler/test_integration.py` — Added doc generator e2e test
