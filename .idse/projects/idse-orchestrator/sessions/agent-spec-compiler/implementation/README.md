# Implementation: idse-orchestrator

Session: agent-spec-compiler  
Stack: python  
Updated: 2026-02-12

## Architecture

The compiler pipeline remains `load -> parse -> merge -> validate -> emit`. This implementation adds a Profiler pre-compiler layer:

`intake -> profiler schema validation -> enforcement heuristics -> deterministic mapper -> AgentProfileSpec JSON`

Profiler lives in `src/idse_orchestrator/profiler/` and is exposed by CLI commands:
- `idse profiler intake`
- `idse profiler export-schema`

## What Was Built

1. Added Profiler package with explicit data contracts:
- `models.py`: ObjectiveFunction, CoreTask, AuthorityBoundary, OutputContract, MissionContract, PersonaOverlay, AgentSpecProfilerDoc
- `models.py`: ProfilerError, ProfilerRejection, ProfilerAcceptance
- `error_codes.py`: 18 canonical error codes

2. Added rules engine (`validate.py`) for enforcement heuristics:
- Generic objective language detection
- Multi-objective transformation detection
- Measurability checks for success metrics
- Structural checks for exclusions/constraints/failures and output contract requirements

3. Added deterministic mapper:
- `map_to_agent_profile_spec.py::to_agent_profile_spec()`
- No inference, direct field mapping from profiler doc to AgentProfileSpec-shaped output

4. Added interactive intake workflow:
- `profiler/cli.py` collects the 20-question flow
- Produces `ProfilerRejection` with `errors + next_questions` or `ProfilerAcceptance`

5. Added schema export:
- `schema.py::export_profiler_json_schema()`
- CLI `idse profiler export-schema --out <path>`

6. Added example profiler documents:
- `src/idse_orchestrator/profiler/examples/restaurant_blog_writer.profiler.json`
- `src/idse_orchestrator/profiler/examples/data_scientist.profiler.json`

7. Added tests:
- `tests/test_profiler/test_validate.py`
- `tests/test_profiler/test_mapper.py`
- `tests/test_profiler/test_cli_profiler.py`

## Validation Reports

Commands executed:
- `PYTHONPATH=src pytest -q tests/test_profiler`
  - Result: `11 passed`
- `PYTHONPATH=src pytest -q tests/test_compiler tests/test_profiler tests/test_cli.py`
  - Result: `48 passed`
- `PYTHONPATH=src python3 -m idse_orchestrator.cli --help`
  - Result: `profiler` command group listed in help output

## Deviations from Plan

- No architectural deviations.
- JSON Schema export was implemented (optional phase) to complete Phase 8 scope.

## Component Declarations

| Component | Action | Type | Parent Primitive |
|---|---|---|---|
| `ProfilerModels` (`src/idse_orchestrator/profiler/models.py`) | Created | Operation | `DocToAgentProfileSpecCompiler` |
| `ProfilerErrorCodes` (`src/idse_orchestrator/profiler/error_codes.py`) | Created | Operation | `DocToAgentProfileSpecCompiler` |
| `ProfilerValidationEngine` (`src/idse_orchestrator/profiler/validate.py`) | Created | Operation | `DocToAgentProfileSpecCompiler` |
| `ProfilerMapper` (`src/idse_orchestrator/profiler/map_to_agent_profile_spec.py`) | Created | Operation | `DocToAgentProfileSpecCompiler` |
| `ProfilerSchemaExport` (`src/idse_orchestrator/profiler/schema.py`) | Created | Infrastructure | `DocToAgentProfileSpecCompiler` |
| `ProfilerIntakeCLI` (`src/idse_orchestrator/profiler/cli.py`) | Created | Routing | `CLIInterface` |
| `CLI profiler commands` (`src/idse_orchestrator/cli.py`) | Modified | Routing | `CLIInterface` |
| `Profiler tests` (`tests/test_profiler/*`) | Created | Artifact | `DocToAgentProfileSpecCompiler` |

## Files Touched

- `src/idse_orchestrator/cli.py`
- `src/idse_orchestrator/profiler/__init__.py`
- `src/idse_orchestrator/profiler/error_codes.py`
- `src/idse_orchestrator/profiler/models.py`
- `src/idse_orchestrator/profiler/validate.py`
- `src/idse_orchestrator/profiler/map_to_agent_profile_spec.py`
- `src/idse_orchestrator/profiler/cli.py`
- `src/idse_orchestrator/profiler/schema.py`
- `src/idse_orchestrator/profiler/examples/restaurant_blog_writer.profiler.json`
- `src/idse_orchestrator/profiler/examples/data_scientist.profiler.json`
- `tests/test_profiler/test_validate.py`
- `tests/test_profiler/test_mapper.py`
- `tests/test_profiler/test_cli_profiler.py`
- `.idse/projects/idse-orchestrator/sessions/agent-spec-compiler/implementation/README.md`
