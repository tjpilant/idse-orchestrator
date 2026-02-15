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

The **Agent Spec Profiler** is a **formalized capture pipeline** that transforms fuzzy agent ideas into complete, validated IDSE-style specification documents. Think of it as an **HR job analysis tool** that:

1. Conducts a structured 20-question intake (like a job interview)
2. Analyzes responses using enforcement rules (the "psychoanalysis" phase)
3. Generates a complete IDSE pipeline document with Intent, Context, Tasks, and Spec sections
4. Embeds a validated `## Agent Profile` YAML block ready for ZCompiler consumption

**What makes it different from manual spec writing:**
- The Profiler is the **only legal way** to create AgentProfileSpec documents
- It's the **front-end type checker** for agents (sits between IDSE cognition and ZPromptCompiler)
- It prevents vague agents from ever compiling by enforcing non-negotiable constraints

**Output:** A complete spec.md file structured like an IDSE pipeline artifact, containing:
- `## Intent` — What is the agent for? (derived from objective_function)
- `## Context` — What constraints apply? (derived from authority_boundary + constraints)
- `## Tasks` — What will it perform? (derived from core_tasks with task + method pairs)
- `## Specification` — Formal requirements (derived from output_contract + failure_conditions)
- `## Agent Profile` — YAML block (deterministic mapping from mission_contract + persona_overlay)

### Problem Statement

Current gap: Users can write freeform `## Agent Profile` YAML blocks with:
- Generic objectives ("be helpful", "assist with anything")
- Multi-objective agents (violates single-responsibility)
- Non-measurable success metrics
- Missing constraints, exclusions, or failure conditions
- Vague core tasks without methods
- No supporting context or intent documentation

The Profiler enforces **structural and semantic constraints** at intake time, ensuring every AgentProfileSpec is:
1. Single-mission (one primary transformation)
2. Specific (no generic language)
3. Measurable (success metric with numbers or proxies)
4. Scoped (explicit exclusions)
5. Checkable (failure conditions + validation rules)
6. **Documented** (complete spec.md with Intent/Context/Tasks/Spec sections, not just YAML)

### Profiler Architecture

**Current (Validation-Only)**:
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

**Required (Full Pipeline Document Generation)**:
```
Phase 1: Intake (20+ questions - HR job interview style)
    │
    ├─ Mission Contract Questions (15 Qs)
    │  ├─ Objective Function (input/output/transformation)
    │  ├─ Success Metric
    │  ├─ Explicit Exclusions
    │  ├─ Core Tasks + Methods
    │  ├─ Authority Boundary (may/may_not)
    │  ├─ Constraints
    │  ├─ Failure Conditions
    │  └─ Output Contract (format/sections/validation)
    │
    └─ Persona Overlay Questions (5 Qs)
       ├─ Industry Context
       ├─ Tone
       ├─ Detail Level
       ├─ Reference Preferences
       └─ Communication Rules
    │
    ▼
Phase 2: Validation ("Psychoanalysis")
    │
    ▼
AgentSpecProfilerDoc (Pydantic schema validation)
    │
    ▼
Enforcement Rules Engine (18 canonical error codes)
    │
    ├─ REJECTED → ProfilerRejection
    │  ├─ errors: [{field, code, message}]
    │  └─ next_questions: ["clarifying question 1", ...]
    │
    └─ ACCEPTED → continue to generation
    │
    ▼
Phase 3: Document Generation (HR job description style)
    │
    ▼
Document Generator produces complete spec.md:
    │
    ├─ ## Intent
    │  └─ Derived from objective_function + success_metric
    │
    ├─ ## Context
    │  └─ Derived from authority_boundary + constraints + explicit_exclusions
    │
    ├─ ## Tasks
    │  └─ Derived from core_tasks (each with task + method)
    │
    ├─ ## Specification
    │  ├─ Overview (transformation_summary)
    │  ├─ Functional Requirements (core_tasks mapped to FR-N format)
    │  ├─ Non-Functional Requirements (constraints + output_contract)
    │  ├─ Acceptance Criteria (success_metric + validation_rules)
    │  └─ Assumptions/Constraints/Dependencies (explicit_exclusions + constraints)
    │
    └─ ## Agent Profile (YAML block)
       └─ Generated via to_agent_profile_spec() deterministic mapping
    │
    ▼
Output: Complete spec.md ready for ZCompiler
```

The **Document Generator** is the missing component. It performs "psychoanalysis" of the mission contract to generate:
- Human-readable prose sections (Intent, Context narrative)
- Structured requirement lists (FR-1, FR-2, ..., AC-1, AC-2, ...)
- Task breakdowns (like HR job descriptions with responsibilities + methods)
- Embedded YAML block (for ZCompiler consumption)

### Canonical Error Codes

The Profiler rejects with structured diagnostics (like a type checker). Error codes have stable numeric IDs for telemetry and cross-platform tracking.

**Errors (E1000-E1999)** — Validation failures that block acceptance:

- `E1000` — `missing_required_field` — Required field is empty or null
- `E1001` — `generic_objective_function` — Objective uses generic language ("be helpful", "assist with anything")
- `E1002` — `multi_objective_agent` — Agent attempts multiple primary transformations (violates single-responsibility)
- `E1003` — `missing_success_metric` — No measurable success criterion defined
- `E1004` — `non_measurable_success_metric` — Success metric has no numbers, percentages, or time units
- `E1005` — `missing_explicit_exclusions` — No explicit exclusions defined (scope unbounded)
- `E1006` — `too_many_core_tasks` — More than 8 core tasks (agent is over-scoped)
- `E1007` — `missing_task` — Core task description is empty
- `E1008` — `non_actionable_method` — Method is platitude not operational ("best practices", "leverage AI", "use common sense")
- `E1009` — `missing_authority_boundary` — Authority boundary not defined
- `E1010` — `missing_may_not` — Authority boundary missing explicit prohibitions (creates permission hole)
- `E1011` — `missing_constraints` — No constraints defined
- `E1012` — `missing_failure_conditions` — No failure conditions defined
- `E1013` — `missing_output_contract` — Output contract not specified
- `E1014` — `invalid_format_type` — Output format_type not in allowed values
- `E1015` — `missing_required_sections` — Required sections for narrative/hybrid output not specified
- `E1016` — `missing_validation_rules` — No validation rules defined in output contract
- `E1017` — `scope_contradiction` — Explicit exclusions contradict core_tasks or output_contract sections
- `E1018` — `output_contract_incoherent` — format_type conflicts with validation_rules (e.g., json format with markdown validation)

**Warnings (W2000-W2999)** — Heuristic signals that may indicate issues but don't block acceptance:

- `W2001` — `persona_leak_into_mission` — Persona-level preferences detected in mission_contract fields
- `W2002` — `success_metric_not_locally_verifiable` — Success metric requires tools/data agent doesn't have authority to access

Each rejection includes:
- `errors: List[ProfilerError]` — field, code (numeric ID), message, severity ("error" | "warning")
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

### CLI Intake Flow (Complete Pipeline)

The Profiler CLI implements a **3-phase pipeline**:

#### Phase 1: Intake (20 structured questions)

**Mission Contract Questions (15 questions):**
1. Input description — "What does this agent take as input?"
2. Output description — "What does this agent produce as output?"
3. Transformation summary — "In one sentence, describe the transformation from input to output"
4. Success metric — "How will you know this agent is successful? What measurable outcome should improve?"
5. Explicit exclusions — "What kinds of problems is this agent explicitly NOT responsible for?"
6. Core tasks (1-8) — "List a core task this agent must perform"
7. Methods for each task — "How should the agent perform that task?"
8. Authority: may — "What is the agent allowed to do?"
9. Authority: may_not — "What is the agent explicitly not allowed to do?"
10. Constraints — "List any operational constraints (limits, policies, guardrails)"
11. Failure conditions — "In practice, what would you consider a failure for this agent?"
12. Output format type — "What kind of output should this agent produce? (narrative/json/hybrid)"
13. Required sections — "What sections must be present in the response?"
14. Required metadata — "What metadata must be included?"
15. Validation rules — "How can we automatically check the output is valid?"

**Persona Overlay Questions (5 questions):**
16. Industry context — "In what industry or domain will this agent operate?"
17. Tone — "What tone should it use?"
18. Detail level — "What level of detail should it default to?"
19. Reference preferences — "Any preferences about references or citations?"
20. Communication rules — "Any communication rules? (e.g., no emojis, always include TL;DR)"

#### Phase 2: Validation ("Psychoanalysis")

After collection:
1. **Pydantic validation** — Schema conformance (non-empty required fields, type checks)
2. **Enforcement validation** — Heuristic rules (18 canonical error codes)
   - Generic language detection
   - Multi-objective detection
   - Measurability check
   - Structural completeness (authority without constraints, tasks without methods, etc.)

**Outcomes:**
- **REJECTED** → Display structured errors + next_questions, allow refinement
- **ACCEPTED** → Proceed to Phase 3

#### Phase 3: Document Generation

Generate complete spec.md file:

1. **## Intent** (generated prose):
   - Goal: `<derived from transformation_summary>`
   - Problem/Opportunity: `<derived from objective_function + explicit_exclusions>`
   - Stakeholders: `<derived from industry_context or default "agent consumers">`
   - Success Criteria: `<derived from success_metric>`
   - Constraints: `<derived from constraints>`

2. **## Context** (generated prose):
   - Architectural constraints narrative
   - Authority boundaries explanation
   - Explicit exclusions rationale

3. **## Tasks** (generated list):
   - Each core_task formatted as:
     ```
     - Task N — <task description>
       Method: <method description>
     ```

4. **## Specification** (generated structured requirements):
   - **Overview**: `<transformation_summary expanded into 2-3 sentences>`
   - **Functional Requirements**: Each core_task becomes FR-N
     ```
     - FR-1: Agent MUST <task 1>
     - FR-2: Agent MUST <task 2>
     ```
   - **Non-Functional Requirements**: Derived from constraints + output_contract
   - **Acceptance Criteria**: Derived from success_metric + validation_rules
     ```
     - AC-1: <success_metric check>
     - AC-2: <validation_rule 1>
     - AC-3: <validation_rule 2>
     ```
   - **Assumptions/Constraints/Dependencies**: `<constraints + explicit_exclusions>`

5. **## Agent Profile** (YAML block):
   - Generated via `to_agent_profile_spec()` deterministic mapping
   - Contains all AgentProfileSpec fields ready for ZCompiler

**Output:** Complete spec.md written to `<agent-name>/specs/spec.md` or stdout

### Folder Structure

```
src/idse_orchestrator/profiler/
  __init__.py
  models.py                       # Pydantic schemas (AgentSpecProfilerDoc, MissionContract, PersonaOverlay, etc.)
  validate.py                     # Enforcement rules engine (validate_profiler_doc, 18 error codes)
  map_to_agent_profile_spec.py   # Deterministic mapper (ProfilerDoc → AgentProfileSpec YAML)
  generate_spec_document.py       # NEW: Document generator (ProfilerDoc → complete spec.md)
  cli.py                          # Interactive 20-question intake + 3-phase pipeline orchestration
  error_codes.py                  # Error code enum (optional)
  examples/
    restaurant_blog_writer.profiler.json
    restaurant_blog_writer.spec.md       # Example generated output
    data_scientist.profiler.json
    data_scientist.spec.md               # Example generated output
```

**New component:** `generate_spec_document.py`

This module contains:
- `generate_intent_section(doc: AgentSpecProfilerDoc) -> str`
- `generate_context_section(doc: AgentSpecProfilerDoc) -> str`
- `generate_tasks_section(doc: AgentSpecProfilerDoc) -> str`
- `generate_specification_section(doc: AgentSpecProfilerDoc) -> str`
- `generate_agent_profile_yaml(doc: AgentSpecProfilerDoc) -> str`
- `generate_complete_spec_md(doc: AgentSpecProfilerDoc) -> str` (orchestrates all above)

Each generator function produces **human-readable prose** (not templates), styled like HR job descriptions with analysis.

### Functional Requirements (Profiler Extension)

**Intake Phase:**
- **PFR-1**: Profiler CLI MUST prompt for all 20 mission contract + persona fields sequentially
- **PFR-2**: Profiler MUST save partial progress (allow resume if intake interrupted)

**Validation Phase ("Psychoanalysis"):**
- **PFR-3**: Profiler MUST reject generic language ("be helpful", "anything", etc.) using GENERIC_PHRASES detection
- **PFR-4**: Profiler MUST reject multi-objective transformations (heuristic: "and/or" chains, multiple verbs)
- **PFR-5**: Profiler MUST enforce measurable success metrics (contains %, numbers, time units, or measurable proxies)
- **PFR-6**: Profiler MUST require non-empty explicit_exclusions, constraints, failure_conditions
- **PFR-7**: Profiler MUST validate core_tasks list is 1-8 items, each with task + method
- **PFR-8**: Profiler MUST validate authority_boundary has both may + may_not (no authority without constraints)
- **PFR-9**: Profiler MUST validate output_contract has validation_rules
- **PFR-10**: Profiler MUST return structured ProfilerRejection with errors + next_questions on validation failure

**Document Generation Phase:**
- **PFR-11**: Profiler MUST generate complete spec.md file with ## Intent, ## Context, ## Tasks, ## Specification sections
- **PFR-12**: Generated ## Intent MUST include Goal, Problem/Opportunity, Stakeholders, Success Criteria (derived from mission_contract)
- **PFR-13**: Generated ## Context MUST include architectural constraints, authority boundaries, and explicit exclusions
- **PFR-14**: Generated ## Tasks MUST list core_tasks with both task descriptions AND methods
- **PFR-15**: Generated ## Specification MUST include Overview, Functional Requirements (FR-1, FR-2, ...), Non-Functional Requirements, Acceptance Criteria (AC-1, AC-2, ...), and Assumptions/Constraints/Dependencies
- **PFR-16**: Generated spec.md MUST contain embedded `## Agent Profile` YAML block (via to_agent_profile_spec() deterministic mapping)
- **PFR-17**: Document Generator MUST produce human-readable prose (not just bullet points), styled like HR job descriptions with analysis
- **PFR-18**: Profiler output MUST be ready for ZCompiler consumption without manual editing

**Production Hardening Phase:**
- **PFR-19**: AgentSpecProfilerDoc MUST include `schema_version` field (default "1.0") for evolution tracking
- **PFR-20**: Generated ## Agent Profile YAML MUST include `profiler_hash` comment (SHA256 of normalized ProfilerDoc) for drift detection
- **PFR-21**: SessionLoader MUST warn when loading spec.md with missing or mismatched profiler_hash (indicates manual edits)
- **PFR-22**: Profiler MUST detect scope contradictions between explicit_exclusions, core_tasks, and output_contract sections (error E1017)
- **PFR-23**: Profiler SHOULD warn when success_metric requires tools/data not in authority_boundary.may (warning W2002)
- **PFR-24**: Profiler MUST reject output_contract incoherence (e.g., format="json" with markdown-specific validation_rules) (error E1018)
- **PFR-25**: Profiler MUST reject non-actionable methods (platitudes like "best practices", "leverage AI") (error E1008)

**UX Enhancement Phase (Phase 10.5):**
- **PFR-26**: Profiler intake MUST support `--save-answers` flag to save collected answers to JSON file before validation
- **PFR-27**: Profiler intake MUST support `--from-json` flag to load answers from JSON file and skip interactive prompts
- **PFR-28**: JSON save/load functions MUST use deterministic serialization (sorted keys, UTF-8, compact separators)
- **PFR-29**: Profiler command group SHOULD be extracted to separate module (`profiler/commands.py`) to prevent main CLI bloat

### Acceptance Criteria (Profiler Extension)

**Intake:**
- **PAC-1**: Profiler CLI completes full 20-question intake without crashes
- **PAC-2**: Profiler saves partial progress and allows resume
- **PAC-27**: `idse profiler intake --save-answers answers.json` creates valid JSON file with all 20 answers
- **PAC-28**: `idse profiler intake --from-json answers.json --spec-out agent.spec.md` generates spec.md without interactive prompts
- **PAC-29**: Edit-retry workflow (save → edit JSON → reload → validate) works correctly when correcting validation errors

**Validation:**
- **PAC-3**: Profiler rejects generic objective ("be helpful with code") with `generic_objective_function` error
- **PAC-4**: Profiler rejects multi-objective transformation ("code reviews and marketing copy") with `multi_objective_agent` error
- **PAC-5**: Profiler rejects non-measurable success metric ("improve quality") with `non_measurable_success_metric` error
- **PAC-6**: Profiler rejects missing failure_conditions with `missing_failure_conditions` error
- **PAC-7**: Profiler rejection includes next_questions list to guide correction
- **PAC-8**: Profiler accepts valid mission contract and proceeds to document generation

**Document Generation:**
- **PAC-9**: Generated spec.md contains all required sections: ## Intent, ## Context, ## Tasks, ## Specification, ## Agent Profile
- **PAC-10**: Generated ## Intent reads like a project charter (Goal, Problem, Stakeholders, Success Criteria)
- **PAC-11**: Generated ## Context includes prose narrative about constraints and boundaries (not just bullet lists)
- **PAC-12**: Generated ## Tasks lists all core_tasks with task + method pairs
- **PAC-13**: Generated ## Specification includes numbered FR-1..FR-N and AC-1..AC-N requirements
- **PAC-14**: Generated ## Agent Profile YAML block validates against AgentProfileSpec schema
- **PAC-15**: Generated spec.md can be fed directly to `idse compile agent-spec` without manual editing
- **PAC-16**: Generated spec.md reads like an HR job description with analysis (not robotic/templated)

**Production Hardening:**
- **PAC-17**: Profiler rejects "Vague Multi-Tasker" spec with E1001, E1002, E1004 error codes
- **PAC-18**: Profiler rejects agent with 9 core tasks with E1006 error code
- **PAC-19**: Profiler rejects authority boundary missing may_not with E1010 error code
- **PAC-20**: Profiler accepts valid "Restaurant Marketing Blog Writer" spec and generates complete spec.md
- **PAC-21**: Profiler rejects "Contradiction Spec" (exclusions contradict core_tasks) with E1017 error code
- **PAC-22**: Profiler warns for "Unverifiable Success Metric" (needs unavailable tools) with W2002 warning
- **PAC-23**: Profiler rejects "Output Contract Mismatch" (json format with markdown rules) with E1018 error code
- **PAC-24**: Generated ## Agent Profile YAML contains `# profiler_hash: <sha256>` comment
- **PAC-25**: SessionLoader logs warning when profiler_hash missing or mismatched on spec.md load
- **PAC-26**: AgentSpecProfilerDoc includes schema_version field, defaults to "1.0"

### Integration with Compiler

**Updated Complete Flow (Profiler → ZCompiler)**:

```
User → idse profiler intake --agent-name <name>
     │
     ├─ Phase 1: 20-question intake
     │  └─ Collects mission_contract + persona_overlay
     │
     ├─ Phase 2: Validation ("Psychoanalysis")
     │  ├─ Pydantic schema validation
     │  ├─ Enforcement rules (18 error codes)
     │  │
     │  ├─ REJECTED → Show errors + next_questions, allow refinement
     │  └─ ACCEPTED → Continue
     │
     └─ Phase 3: Document Generation
        ├─ generate_complete_spec_md(doc)
        │  ├─ ## Intent (prose from objective_function + success_metric)
        │  ├─ ## Context (prose from authority_boundary + constraints)
        │  ├─ ## Tasks (list from core_tasks with methods)
        │  ├─ ## Specification (FR-N, AC-N from core_tasks + validation_rules)
        │  └─ ## Agent Profile (YAML from to_agent_profile_spec())
        │
        └─ Write to .idse/agents/<agent-name>/specs/spec.md
     │
     ▼
idse compile agent-spec --session <agent-name>
     │
     ├─ SessionLoader reads spec.md from SQLite
     ├─ parse_agent_profile() extracts ## Agent Profile YAML
     ├─ merge_profiles() (if blueprint exists)
     ├─ AgentProfileSpec validation
     └─ emit_profile() → <agent-name>.profile.yaml
     │
     ▼
ZPromptCompiler consumes .profile.yaml
```

**Key insight:** The Profiler generates the **complete spec.md** that the existing compiler expects. There's no manual step - the output is ZCompiler-ready.

### Command Examples

**Generate agent spec from intake:**
```bash
idse profiler intake --agent-name code-reviewer --out-dir .idse/agents/code-reviewer/specs/
```

**Compile generated spec to .profile.yaml:**
```bash
idse compile agent-spec --session code-reviewer --project my-project
```

**One-shot (intake + compile):**
```bash
idse profiler create-agent --name code-reviewer
# Runs intake → validation → document generation → compilation
```

### Next Implementation Priority

**Phase 1 (MVP)**: Document generator + 3-phase CLI
- Implement `generate_spec_document.py` with all section generators
- Wire into CLI as `idse profiler intake`
- Manual examples for 2 agent types (code reviewer, data analyst)

**Phase 2**: Refinement loop
- Auto-ask next_questions when validation fails
- Allow partial save/resume during intake

**Phase 3**: JSON Schema export
- Generate JSON Schema from Pydantic for platform-neutral validation
- Enable web UI or Notion-based intake flows
