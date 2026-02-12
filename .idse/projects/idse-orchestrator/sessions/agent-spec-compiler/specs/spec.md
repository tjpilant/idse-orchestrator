# Specification

## Overview
Audit and harden the existing DocToAgentProfileSpec compiler to close gaps identified in context.md. The compiler already exists with full pipeline (load → parse → merge → validate → emit). This session focuses on: SQLite-backed loading, end-to-end validation, schema documentation, and mapping rules.

## Functional Requirements

- FR-1: `SessionLoader` MUST read spec.md content from SQLite via `ArtifactDatabase.load_artifact()`, falling back to filesystem only when DB is unavailable.
- FR-2: `compile_agent_spec()` MUST accept a `backend` parameter to select SQLite or filesystem loading.
- FR-3: The compiler MUST produce a valid `AgentProfileSpec` YAML file at `.idse/projects/<project>/build/agents/<session>.profile.yaml`.
- FR-4: The compiler MUST validate all required fields (`id`, `name`) are present and non-empty.
- FR-5: The compiler MUST apply blueprint-to-feature inheritance: feature overrides blueprint where explicitly specified; blueprint provides defaults otherwise.
- FR-6: The `--dry-run` flag MUST print validated YAML to stdout without writing files.
- FR-7: The compiler MUST NOT call LLMs, external APIs, or import PromptBraining modules.

## Non-Functional Requirements
- Deterministic output: same inputs MUST produce byte-identical output (excluding timestamp comment)
- Schema version tracked in output: `version: "1.0"` field
- No new dependencies beyond what's in `pyproject.toml`

## Acceptance Criteria
- AC-1: `idse compile agent-spec --session agent-spec-compiler --project idse-orchestrator --dry-run` produces valid YAML from the `## Agent Profile` block in this spec.md
- AC-2: `SessionLoader` loads from SQLite when backend is sqlite
- AC-3: Compilation with missing required fields (`id`, `name`) raises `ValidationError`
- AC-4: Blueprint + feature merge produces expected override behavior
- AC-5: All existing compiler tests continue to pass (7 tests)
- AC-6: At least 3 new tests covering SQLite loading, end-to-end compilation, and validation errors

## Assumptions / Constraints / Dependencies
- Assumptions: `ArtifactDatabase` API is stable; `load_artifact()` returns content with `## Agent Profile` YAML block intact
- Constraints: No runtime dependencies; no PromptBraining imports
- Dependencies: `compiler/` package (existing), `ArtifactDatabase` (existing)

## AgentProfileSpec Schema

### Current Fields (Pydantic model in `compiler/models.py`)

| Field | Type | Required | Description |
|---|---|---|---|
| `id` | `str` | Yes | Stable identifier (e.g., `auth-service-agent`) |
| `name` | `str` | Yes | Human-readable name |
| `description` | `str` | No | Short summary of role and scope |
| `goals` | `List[str]` | No | Explicit goals for the agent |
| `inputs` | `List[str]` | No | Input types or schemas |
| `outputs` | `List[str]` | No | Output types or artifacts |
| `tools` | `List[str]` | No | Tool names the runtime may use |
| `constraints` | `List[str]` | No | Safety, cost, scope constraints |
| `memory_policy` | `Dict[str, Any]` | No | Named memory policies |
| `runtime_hints` | `Dict[str, Any]` | No | Non-required runtime preferences |
| `version` | `str` | No | Schema version (default `"1.0"`) |
| `source_session` | `str` | No | Provenance: originating session |
| `source_blueprint` | `str` | No | Provenance: blueprint session used |

### Mapping Rules (spec.md → AgentProfileSpec)

The `## Agent Profile` section in `spec.md` contains a fenced YAML block that maps directly to `AgentProfileSpec` fields. The parser (`compiler/parser.py`) extracts the first `yaml` code block under the `## Agent Profile` heading.

Inheritance: Blueprint `spec.md` Agent Profile provides defaults. Feature `spec.md` Agent Profile overrides. Deep merge for dicts; replacement for lists and scalars.

## Agent Profile

```yaml
id: agent-spec-compiler
name: AgentSpecCompiler Audit Session
description: Validates and hardens the DocToAgentProfileSpec compiler pipeline
goals:
  - Ensure SessionLoader reads from SQLite backend
  - Validate end-to-end compilation from spec.md to .profile.yaml
  - Document AgentProfileSpec schema and mapping rules
inputs:
  - spec.md with Agent Profile YAML block
  - Blueprint spec.md for inheritance defaults
outputs:
  - Validated .profile.yaml file
  - Schema documentation
tools:
  - Click CLI
  - Pydantic v2
  - PyYAML
constraints:
  - No LLM calls
  - No PromptBraining runtime imports
  - Deterministic output
memory_policy: {}
runtime_hints: {}
version: "1.0"
```

---

## Agent Spec Profiler Extension (Scope Expansion 2026-02-11)

### Overview

The **Agent Spec Profiler** is a structured intake and validation layer that sits **before** the AgentProfileSpec compiler. It enforces "no vibes" mission contracts by collecting structured responses via CLI or UI, validating against heuristic rules, and producing a normalized `AgentSpecProfilerDoc` that maps deterministically to `AgentProfileSpec` format.

### Problem Statement

Current gap: Users can write freeform `## Agent Profile` YAML blocks with:
- Generic objectives ("be helpful", "assist with anything")
- Multi-objective agents (violates single-responsibility)
- Non-measurable success metrics
- Missing constraints, exclusions, or failure conditions
- Vague core tasks without methods

The Profiler enforces **structural and semantic constraints** before compilation, ensuring every AgentProfileSpec is:
1. Single-mission (one primary transformation)
2. Specific (no generic language)
3. Measurable (success metric with numbers or proxies)
4. Scoped (explicit exclusions)
5. Checkable (failure conditions + validation rules)

### Profiler Architecture

```
CLI/UI Intake Questions
    │
    ▼
AgentSpecProfilerDoc (Pydantic validation)
    │
    ▼
Enforcement Rules Engine (heuristics + structured errors)
    │
    ├─ REJECTED → ProfilerRejection (errors + next_questions)
    │
    └─ ACCEPTED → to_agent_profile_spec() mapper
           │
           ▼
       AgentProfileSpec (compiler input)
```

### Canonical Error Codes

The Profiler rejects with structured diagnostics (like a type checker):

- `missing_required_field`
- `generic_objective_function`
- `multi_objective_agent`
- `missing_success_metric`
- `non_measurable_success_metric`
- `missing_explicit_exclusions`
- `too_many_core_tasks`
- `missing_task`
- `missing_method`
- `missing_authority_boundary`
- `missing_may_not`
- `missing_constraints`
- `missing_failure_conditions`
- `missing_output_contract`
- `invalid_format_type`
- `missing_required_sections`
- `missing_validation_rules`
- `persona_leak_into_mission` (optional heuristic)

Each rejection includes:
- `errors: List[ProfilerError]` — field, code, message
- `next_questions: List[str]` — clarifying questions to fix the issue

### Profiler Data Model (Pydantic)

**AgentSpecProfilerDoc** (input schema):

```python
class ObjectiveFunction(BaseModel):
    input_description: str  # min 3 chars
    output_description: str  # min 3 chars
    transformation_summary: str  # min 5 chars

class CoreTask(BaseModel):
    task: str  # min 2 chars
    method: str  # min 2 chars

class AuthorityBoundary(BaseModel):
    may: List[str]  # min 1 item
    may_not: List[str]  # min 1 item

class OutputContract(BaseModel):
    format_type: Literal["narrative", "json", "hybrid"]
    required_sections: List[str]  # non-empty for narrative/hybrid
    required_metadata: List[str]
    validation_rules: List[str]  # min 1 item

class MissionContract(BaseModel):
    objective_function: ObjectiveFunction
    success_metric: str  # min 3 chars
    explicit_exclusions: List[str]  # min 1 item
    core_tasks: List[CoreTask]  # 1-8 items
    authority_boundary: AuthorityBoundary
    constraints: List[str]  # min 1 item
    failure_conditions: List[str]  # min 1 item
    output_contract: OutputContract

class PersonaOverlay(BaseModel):
    industry_context: Optional[str]
    tone: Optional[str]
    detail_level: Optional[str]
    reference_preferences: List[str]
    communication_rules: List[str]

class AgentSpecProfilerDoc(BaseModel):
    mission_contract: MissionContract
    persona_overlay: PersonaOverlay
```

### Enforcement Heuristics

Beyond Pydantic validation, the `validate_profiler_doc()` function applies:

1. **Generic language detection**: Rejects "be helpful", "assist with anything", "various outputs", etc.
2. **Multi-objective detection**: Rejects transformation summaries with "and/or" chains or multiple verbs
3. **Measurability check**: Success metric must contain %, numbers, time units, or measurable proxies
4. **Structural completeness**: All required lists/boundaries must be non-empty

If validation fails, returns `ProfilerRejection` with structured errors + next_questions.

### Profiler → AgentProfileSpec Mapper

The `to_agent_profile_spec()` function is **deterministic** (no inference):

```python
def to_agent_profile_spec(doc: AgentSpecProfilerDoc) -> Dict[str, Any]:
    mc = doc.mission_contract
    po = doc.persona_overlay

    return {
        "name": None,  # filled by caller
        "description": mc.objective_function.transformation_summary,
        "objective_function": {
            "input_description": mc.objective_function.input_description,
            "output_description": mc.objective_function.output_description,
            "transformation_summary": mc.objective_function.transformation_summary,
        },
        "success_criteria": mc.success_metric,
        "out_of_scope": mc.explicit_exclusions,
        "capabilities": [
            {"task": t.task, "method": t.method} for t in mc.core_tasks
        ],
        "action_permissions": {
            "may": mc.authority_boundary.may,
            "may_not": mc.authority_boundary.may_not,
        },
        "constraints": mc.constraints,
        "failure_modes": mc.failure_conditions,
        "output_contract": {
            "format_type": mc.output_contract.format_type,
            "required_sections": mc.output_contract.required_sections,
            "required_metadata": mc.output_contract.required_metadata,
            "validation_rules": mc.output_contract.validation_rules,
        },
        "persona": {
            "industry_context": po.industry_context,
            "tone": po.tone,
            "detail_level": po.detail_level,
            "reference_preferences": po.reference_preferences,
            "communication_rules": po.communication_rules,
        }
    }
```

### CLI Intake Flow (Minimal Implementation)

The Profiler CLI asks **20 structured questions** sequentially:

1. Input description
2. Output description
3. Transformation summary (one sentence)
4. Success metric (measurable)
5. Explicit exclusions (list)
6. Core tasks (list, max 8)
7. Methods for each task
8. Authority: may (list)
9. Authority: may_not (list)
10. Constraints (list)
11. Failure conditions (list)
12. Output format type
13. Required sections (if narrative/hybrid)
14. Required metadata (optional)
15. Validation rules (list)
16. Industry context (optional)
17. Tone (optional)
18. Detail level (optional)
19. Reference preferences (optional)
20. Communication rules (optional)

After collection:
- Pydantic validation (schema)
- Enforcement validation (heuristics)
- If accepted: emit AgentProfileSpec JSON
- If rejected: display errors + next_questions

### Folder Structure

```
src/idse_orchestrator/profiler/
  __init__.py
  models.py                       # Pydantic schemas
  validate.py                     # Enforcement rules engine
  map_to_agent_profile_spec.py   # Deterministic mapper
  cli.py                          # Interactive intake
  error_codes.py                  # Error code enum (optional)
  examples/
    restaurant_blog_writer.profiler.json
    data_scientist.profiler.json
```

### Functional Requirements (Profiler Extension)

- **PFR-1**: Profiler CLI MUST prompt for all 20 mission contract + persona fields
- **PFR-2**: Profiler MUST reject generic language ("be helpful", "anything", etc.)
- **PFR-3**: Profiler MUST reject multi-objective transformations
- **PFR-4**: Profiler MUST enforce measurable success metrics (with numbers or proxies)
- **PFR-5**: Profiler MUST require non-empty explicit_exclusions, constraints, failure_conditions
- **PFR-6**: Profiler MUST validate core_tasks list is 1-8 items, each with task + method
- **PFR-7**: Profiler MUST validate authority_boundary has both may + may_not
- **PFR-8**: Profiler MUST validate output_contract has validation_rules
- **PFR-9**: Profiler MUST return structured ProfilerRejection with errors + next_questions on failure
- **PFR-10**: Profiler MUST emit deterministic AgentProfileSpec JSON on acceptance

### Acceptance Criteria (Profiler Extension)

- **PAC-1**: Profiler CLI completes full 20-question intake without crashes
- **PAC-2**: Profiler rejects generic objective ("be helpful with code") with `generic_objective_function` error
- **PAC-3**: Profiler rejects multi-objective transformation with `multi_objective_agent` error
- **PAC-4**: Profiler rejects non-measurable success metric with `non_measurable_success_metric` error
- **PAC-5**: Profiler accepts valid mission contract and emits AgentProfileSpec JSON
- **PAC-6**: Profiler rejection includes next_questions list to guide correction
- **PAC-7**: Profiler output can be fed directly to `compile_agent_spec()` compiler

### Integration with Compiler

The Profiler output (AgentProfileSpec dict) becomes the **normalized input** to the existing compiler:

```
User → Profiler CLI (20 questions)
     → AgentSpecProfilerDoc (Pydantic)
     → validate_profiler_doc() (enforcement)
     → to_agent_profile_spec() (mapper)
     → AgentProfileSpec JSON
     → Write to spec.md ## Agent Profile block
     → compile_agent_spec() (existing compiler)
     → .profile.yaml output
```

### Next Implementation Priority

**Option 1 (Pure Python)**: CLI intake loop with validation
**Option 2 (JSON Schema Export)**: Generate JSON Schema from Pydantic for platform-neutral validation
**Option 3 (Refinement Loop)**: Auto-ask next_questions and re-validate until accepted

**Recommended**: Start with Option 1 (CLI) for immediate dogfooding, then add JSON Schema export for cross-platform use.
