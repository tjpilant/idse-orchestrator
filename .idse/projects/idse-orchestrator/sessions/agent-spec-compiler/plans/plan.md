# Plan — agent-spec-compiler

## 0. Product Overview

**Goal / Outcome:**
Harden the existing DocToAgentProfileSpec compiler so it aligns with the "SQLite is source of truth" invariant, passes end-to-end validation, and is documented well enough for PromptBraining to consume its output.

**Problem Statement:**
The compiler was built during initial extraction (Feb 2026) and works against filesystem reads. It has never been exercised against a real project or validated against the blueprint's exit criteria. The `SessionLoader` bypasses SQLite, violating the project's core invariant.

**Target Users:**
- IDSE developers running `idse compile agent-spec` to produce `.profile.yaml`
- CI pipelines automating spec compilation
- PromptBraining (downstream consumer of compiled specs)

**Success Metrics:**
- All acceptance criteria from spec.md pass
- 10+ compiler tests passing (7 existing + 3 new minimum)
- End-to-end: this session's own `spec.md` compiles to a valid `.profile.yaml`

## 1. Architecture Summary

```
spec.md (## Agent Profile YAML block)
    │
    ▼
SessionLoader ──── reads from SQLite (primary) or filesystem (fallback)
    │
    ▼
parse_agent_profile() ──── extracts YAML block under ## Agent Profile
    │
    ▼
merge_profiles() ──── deep-merges blueprint defaults + feature overrides
    │
    ▼
AgentProfileSpec ──── Pydantic validation
    │
    ▼
emit_profile() ──── writes {session}.profile.yaml to build/agents/
```

No changes to this architecture. The work is:
1. Make `SessionLoader` read from SQLite
2. Add tests for the full chain
3. Document the schema and mapping

## 2. Components

| Component | Responsibility | Parent Primitive |
|---|---|---|
| `SessionLoader` | Load spec.md from SQLite or filesystem | `DocToAgentProfileSpecCompiler` |
| `parse_agent_profile` | Extract YAML from `## Agent Profile` heading | `DocToAgentProfileSpecCompiler` |
| `merge_profiles` | Deep-merge blueprint + feature profiles | `DocToAgentProfileSpecCompiler` |
| `AgentProfileSpec` | Pydantic model for validation | `DocToAgentProfileSpecCompiler` |
| `emit_profile` | Write validated YAML to disk | `DocToAgentProfileSpecCompiler` |
| CLI `compile agent-spec` | User-facing command | `CLIInterface` |

## 3. Data Model

`AgentProfileSpec` (Pydantic model — no DB table, output-only):
- `id: str` (required)
- `name: str` (required)
- `description: Optional[str]`
- `goals: List[str]`
- `inputs: List[str]`
- `outputs: List[str]`
- `tools: List[str]`
- `constraints: List[str]`
- `memory_policy: Optional[Dict[str, Any]]`
- `runtime_hints: Optional[Dict[str, Any]]`
- `version: str` (default "1.0")
- `source_session: Optional[str]`
- `source_blueprint: Optional[str]`

## 4. API Contracts

CLI interface (already wired):
```
idse compile agent-spec \
  --session <session_id>       # required
  --project <project_name>     # optional, auto-detect
  --blueprint <blueprint_id>   # optional, default __blueprint__
  --out <output_dir>           # optional, default build/agents/
  --dry-run                    # optional, print YAML to stdout
```

## 5. Test Strategy

- **Existing tests (7):** model validation, parser extraction, emitter output, merger behavior
- **New tests (Phase 2):**
  - SQLite-backed `SessionLoader` reads artifact content correctly
  - End-to-end: `compile_agent_spec()` with filled spec.md produces valid YAML
  - Validation error on missing required fields (`id`, `name`)
  - Blueprint + feature merge override behavior
- **Tool:** pytest

## 6. Phases

### Phase 0 — Audit existing compiler
- Read all 7 modules in `compiler/`
- Run existing tests, confirm 7 pass
- Identify any code-level issues beyond the known gaps

### Phase 1 — SQLite-backed SessionLoader
- Update `SessionLoader` to accept a backend parameter
- When `backend="sqlite"`, load via `ArtifactDatabase.load_artifact(project, session_id, "spec").content`
- Fall back to filesystem when DB is unavailable or backend is explicitly `"filesystem"`
- Update `compile_agent_spec()` to pass backend through

### Phase 2 — Tests and validation
- Add test for SQLite loading path
- Add end-to-end test: create a temp project with filled `## Agent Profile` YAML, compile, validate output
- Add test for missing required fields
- Add test for blueprint + feature merge
- Confirm all tests pass (7 existing + new)

### Phase 3 — Documentation and self-test
- Run `idse compile agent-spec --session agent-spec-compiler --project idse-orchestrator --dry-run` to self-validate
- Write implementation/README.md and feedback/feedback.md
- Sync to DB

---

## Scope Expansion: Agent Spec Profiler (2026-02-11)

The Profiler is an **intake + validation layer** that sits before the compiler. It enforces "no vibes" mission contracts via structured questions, heuristic validation, and deterministic mapping to AgentProfileSpec.

### Phase 4 — Profiler Data Models & Validation

**Components:**
- `AgentSpecProfilerDoc` (Pydantic model for intake)
- `ProfilerError` (structured error diagnostics)
- `ProfilerRejection` (errors + next_questions)
- `ProfilerAcceptance` (normalized doc)

**Sub-components:**
- `ObjectiveFunction` (input/output/transformation)
- `CoreTask` (task + method pairs)
- `AuthorityBoundary` (may + may_not)
- `OutputContract` (format + sections + validation_rules)
- `MissionContract` (full mission spec)
- `PersonaOverlay` (optional styling)

**Validation Rules:**
1. Generic language detection (GENERIC_PHRASES list)
2. Multi-objective detection (heuristic: "and/or" chains)
3. Measurability check (MEASURABLE_HINTS: %, numbers, time units)
4. Structural completeness (non-empty lists, 1-8 core tasks, etc.)

**Files:**
- `src/idse_orchestrator/profiler/models.py`
- `src/idse_orchestrator/profiler/validate.py`
- `src/idse_orchestrator/profiler/error_codes.py` (optional enum)

**Tests:**
- Valid mission contract passes validation
- Generic objective rejected with `generic_objective_function`
- Multi-objective rejected with `multi_objective_agent`
- Non-measurable metric rejected with `non_measurable_success_metric`
- Missing constraints/exclusions/failures rejected
- Empty core_tasks or > 8 tasks rejected
- Missing may_not rejected

### Phase 5 — Profiler Mapper

**Component:**
- `to_agent_profile_spec()` — deterministic mapper from `AgentSpecProfilerDoc` to `AgentProfileSpec` dict

**Mapping logic:**
```python
AgentSpecProfilerDoc.mission_contract.objective_function
  → AgentProfileSpec.objective_function

AgentSpecProfilerDoc.mission_contract.success_metric
  → AgentProfileSpec.success_criteria

AgentSpecProfilerDoc.mission_contract.explicit_exclusions
  → AgentProfileSpec.out_of_scope

AgentSpecProfilerDoc.mission_contract.core_tasks
  → AgentProfileSpec.capabilities (list of {task, method})

AgentSpecProfilerDoc.mission_contract.authority_boundary
  → AgentProfileSpec.action_permissions {may, may_not}

AgentSpecProfilerDoc.mission_contract.constraints
  → AgentProfileSpec.constraints

AgentSpecProfilerDoc.mission_contract.failure_conditions
  → AgentProfileSpec.failure_modes

AgentSpecProfilerDoc.mission_contract.output_contract
  → AgentProfileSpec.output_contract

AgentSpecProfilerDoc.persona_overlay
  → AgentProfileSpec.persona
```

**Files:**
- `src/idse_orchestrator/profiler/map_to_agent_profile_spec.py`

**Tests:**
- Full mission contract maps to complete AgentProfileSpec
- Persona overlay maps to persona field
- Empty persona produces empty persona dict

### Phase 6 — Profiler CLI Intake

**Component:**
- Interactive CLI that prompts 20 questions sequentially
- Collects mission_contract + persona_overlay
- Validates via Pydantic + enforcement rules
- Returns ProfilerRejection (with next_questions) or ProfilerAcceptance

**20 Questions:**
1. Input description
2. Output description
3. Transformation summary
4. Success metric
5-N. Explicit exclusions (list)
N+1-M. Core tasks (list, max 8)
M+1-P. Methods for each task
P+1. Authority: may (list)
P+2. Authority: may_not (list)
P+3. Constraints (list)
P+4. Failure conditions (list)
P+5. Output format type
P+6. Required sections (if narrative/hybrid)
P+7. Required metadata
P+8. Validation rules (list)
P+9. Industry context (optional)
P+10. Tone (optional)
P+11. Detail level (optional)
P+12. Reference preferences (optional)
P+13. Communication rules (optional)

**Files:**
- `src/idse_orchestrator/profiler/cli.py`
- `src/idse_orchestrator/profiler/__init__.py`

**CLI command:**
```bash
idse profiler intake --out <path-to-output.json>
```

**Tests:**
- CLI completes full intake without crashes
- Valid answers produce AgentProfileSpec JSON
- Invalid answers show ProfilerRejection with errors + next_questions

### Phase 7 — Profiler Integration with Compiler

**Flow:**
```
idse profiler intake
  → collects 20 answers
  → validates via Pydantic + rules
  → if rejected: show errors + next_questions, exit
  → if accepted: emit AgentProfileSpec JSON
  → (optional) write to spec.md ## Agent Profile block
  → idse compile agent-spec --session <id>
  → .profile.yaml output
```

**Integration point:**
- Profiler output (AgentProfileSpec dict) can be:
  1. Written to spec.md ## Agent Profile YAML block (manual)
  2. Fed directly to `compile_agent_spec()` (programmatic)

**Files:**
- Update `src/idse_orchestrator/cli.py` to add `profiler` command group
- Wire `profiler intake` subcommand

**Tests:**
- End-to-end: profiler intake → validation → mapper → compiler → .profile.yaml
- Profiler rejection blocks compilation
- Profiler acceptance flows through to valid .profile.yaml

### Phase 8 — JSON Schema Export (Optional)

**Component:**
- Export Pydantic models to JSON Schema for platform-neutral validation

**Files:**
- `src/idse_orchestrator/profiler/schema.py`
- `build/schemas/agent_spec_profiler.schema.json`

**CLI command:**
```bash
idse profiler export-schema --out build/schemas/
```

**Use case:**
- Web UI form validation (JavaScript/TypeScript)
- Notion database property validation
- Cross-platform validation without Python runtime

### Phase 9 — Profiler Documentation & Self-Test

**Deliverables:**
- Document Profiler architecture in implementation/README.md
- Document enforcement rules and error codes
- Document 20-question CLI flow
- Run self-test: create a valid AgentSpecProfilerDoc for this session
- Validate it compiles to valid .profile.yaml

**Acceptance:**
- Profiler docs explain models, validation, mapping, CLI
- Error code reference included
- Examples directory has 2+ .profiler.json files
- Self-test passes
