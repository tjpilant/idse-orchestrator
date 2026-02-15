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

### Phase 5.5 — Profiler Document Generator

**Component:**
- `generate_spec_document.py` — generates complete IDSE spec.md from validated ProfilerDoc

**Sub-components:**
- `generate_intent_section(doc: AgentSpecProfilerDoc) -> str`
  - Produces ## Intent with Goal, Problem/Opportunity, Stakeholders, Success Criteria
  - Derived from objective_function + success_metric + industry_context
  - Human-readable prose (like project charter)

- `generate_context_section(doc: AgentSpecProfilerDoc) -> str`
  - Produces ## Context with architectural constraints narrative
  - Derived from authority_boundary + constraints + explicit_exclusions
  - Explains "why these boundaries" (not just lists)

- `generate_tasks_section(doc: AgentSpecProfilerDoc) -> str`
  - Produces ## Tasks with core_tasks listed with methods
  - Format: `- Task N — <task>` + `Method: <method>`

- `generate_specification_section(doc: AgentSpecProfilerDoc) -> str`
  - Produces ## Specification with:
    - Overview (transformation_summary expanded to 2-3 sentences)
    - Functional Requirements (FR-1..FR-N from core_tasks)
    - Non-Functional Requirements (from constraints + output_contract)
    - Acceptance Criteria (AC-1..AC-N from success_metric + validation_rules)
    - Assumptions/Constraints/Dependencies (from constraints + explicit_exclusions)

- `generate_agent_profile_yaml(doc: AgentSpecProfilerDoc) -> str`
  - Produces ## Agent Profile YAML block
  - Uses `to_agent_profile_spec()` + YAML serialization

- `generate_complete_spec_md(doc: AgentSpecProfilerDoc) -> str`
  - Orchestrates all above generators
  - Assembles complete spec.md document

**Files:**
- `src/idse_orchestrator/profiler/generate_spec_document.py`

**Tests:**
- Each generator function produces non-empty output
- Generated ## Intent includes all required subsections
- Generated ## Specification includes numbered FR-N and AC-N requirements
- Generated ## Agent Profile YAML validates against AgentProfileSpec schema
- Complete spec.md can be parsed by existing `compile_agent_spec()` compiler
- Generated prose reads like HR job description (not robotic templates)

### Phase 6 — Profiler CLI 3-Phase Pipeline

**Component:**
- Interactive CLI that orchestrates **3 phases**: Intake → Validation → Document Generation
- Implements complete "HR job analysis" workflow
- Produces ready-to-compile spec.md file (not just JSON)

**Phase 1: Intake (20 questions)**
Mission Contract Questions (15):
1. Input description
2. Output description
3. Transformation summary
4. Success metric
5. Explicit exclusions (list)
6-13. Core tasks (1-8, each with task + method)
14. Authority: may (list)
15. Authority: may_not (list)
16. Constraints (list)
17. Failure conditions (list)
18. Output format type
19. Required sections (if narrative/hybrid)
20. Required metadata
21. Validation rules (list)

Persona Overlay Questions (5):
22. Industry context (optional)
23. Tone (optional)
24. Detail level (optional)
25. Reference preferences (optional)
26. Communication rules (optional)

**Phase 2: Validation ("Psychoanalysis")**
- Pydantic schema validation
- Enforcement rules engine (18 canonical error codes)
- If rejected: show errors + next_questions, allow refinement
- If accepted: proceed to Phase 3

**Phase 3: Document Generation**
- Call `generate_complete_spec_md(doc)`
- Write to `.idse/agents/<agent-name>/specs/spec.md`
- Display summary + path to user

**Files:**
- `src/idse_orchestrator/profiler/cli.py`
- `src/idse_orchestrator/profiler/__init__.py`
- Update `src/idse_orchestrator/cli.py` to wire `profiler` command group

**CLI commands:**
```bash
# Interactive intake → validation → document generation
idse profiler intake --agent-name <name> [--out-dir <dir>]

# One-shot (intake + compile to .profile.yaml)
idse profiler create-agent --name <name>
```

**Tests:**
- CLI completes full 3-phase pipeline without crashes
- Valid answers produce complete spec.md (not just JSON)
- Invalid answers show ProfilerRejection with errors + next_questions, allow retry
- Generated spec.md contains all sections (Intent, Context, Tasks, Specification, Agent Profile)
- Generated spec.md can be fed to `idse compile agent-spec` without edits

### Phase 7 — Profiler Integration with Compiler

**Complete Flow (Updated):**
```
idse profiler intake --agent-name code-reviewer
  │
  ├─ Phase 1: Collects 20 answers (mission_contract + persona_overlay)
  │
  ├─ Phase 2: Validation
  │  ├─ Pydantic schema validation
  │  ├─ Enforcement rules (18 error codes)
  │  │
  │  ├─ REJECTED → Show errors + next_questions, allow retry
  │  └─ ACCEPTED → Continue
  │
  └─ Phase 3: Document Generation
     ├─ generate_complete_spec_md(doc)
     │  ├─ ## Intent (prose from objective_function)
     │  ├─ ## Context (prose from authority_boundary + constraints)
     │  ├─ ## Tasks (list from core_tasks with methods)
     │  ├─ ## Specification (FR-N, AC-N)
     │  └─ ## Agent Profile (YAML block)
     │
     └─ Write to .idse/agents/code-reviewer/specs/spec.md
  │
  ▼
idse compile agent-spec --session code-reviewer
  │
  ├─ SessionLoader reads spec.md from SQLite or filesystem
  ├─ parse_agent_profile() extracts ## Agent Profile YAML
  ├─ merge_profiles() (if blueprint exists)
  ├─ AgentProfileSpec validation
  └─ emit_profile() → code-reviewer.profile.yaml
  │
  ▼
ZPromptCompiler consumes .profile.yaml
```

**Key Integration Points:**
1. Profiler writes complete spec.md (not just YAML snippet)
2. No manual editing required between Profiler output and compiler input
3. Existing compiler (`compile_agent_spec()`) works unchanged
4. The spec.md contains embedded ## Agent Profile YAML block ready for parsing

**Files:**
- Already wired in Phase 6 CLI updates

**Tests:**
- End-to-end: `profiler intake` → spec.md written → `compile agent-spec` → .profile.yaml
- Profiler rejection prevents spec.md generation (no partial files)
- Generated spec.md validates with existing compiler (no parse errors)
- Round-trip: intake → spec.md → .profile.yaml produces valid AgentProfileSpec

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

---

### Phase 10 — Production Hardening (Adversarial Testing & Drift Detection)

**Objective:**
Harden the Profiler against adversarial inputs, add drift detection for manual spec.md edits, and ensure compile-time invariants are enforced.

**Components:**

1. **Schema Versioning & Hash-Based Drift Detection**
   - Add `schema_version: str = "1.0"` to `AgentSpecProfilerDoc`
   - Compute `profiler_hash` (SHA256 of normalized ProfilerDoc) in `generate_agent_profile_yaml()`
   - Embed hash as YAML comment: `# profiler_hash: <sha256>`
   - Add hash validation in `SessionLoader.load_spec()` — warn on missing/mismatched hash

2. **Additional Error Codes (E1008, E1017, E1018, W2002)**
   - `E1008` — `non_actionable_method` — Method is platitude ("best practices", "leverage AI")
   - `E1017` — `scope_contradiction` — Exclusions contradict core_tasks or output_contract
   - `E1018` — `output_contract_incoherent` — format_type conflicts with validation_rules
   - `W2002` — `success_metric_not_locally_verifiable` — Metric needs tools agent doesn't have

3. **Advanced Validation Rules**
   - `_detect_scope_contradictions()` — Cross-check explicit_exclusions vs core_tasks vs output_contract
   - `_detect_unverifiable_metrics()` — Check if success_metric requires tools not in authority_boundary.may
   - `_detect_output_contract_incoherence()` — Validate format_type vs validation_rules consistency
   - `_detect_non_actionable_methods()` — Flag methods with generic platitudes

4. **Adversarial Test Suite (10 tests)**
   - Test 1: **Vague Multi-Tasker** — Generic objective, multi-objective, non-measurable metric (E1001, E1002, E1004)
   - Test 2: **Over-Scoped Agent** — 9 core tasks (E1006)
   - Test 3: **Authority Hole** — Missing may_not (E1010)
   - Test 4: **Valid Restaurant Blogger** — Golden path acceptance
   - Test 5: **Non-Actionable Methods** — Platitude methods (E1008)
   - Test 6: **Excessive Tasks** — Too many core tasks
   - Test 7: **Generic Language** — Generic objective function
   - Test 8: **Contradiction Spec** — Exclusions contradict tasks (E1017)
   - Test 9: **Unverifiable Success** — Metric needs unavailable tools (W2002)
   - Test 10: **Output Contract Mismatch** — json format with markdown validation (E1018)

**Files:**
- `src/idse_orchestrator/profiler/models.py` — add schema_version field
- `src/idse_orchestrator/profiler/error_codes.py` — add 4 new error codes
- `src/idse_orchestrator/profiler/validate.py` — add 4 new validation functions
- `src/idse_orchestrator/profiler/generate_spec_document.py` — add profiler_hash computation
- `src/idse_orchestrator/compiler/session_loader.py` — add hash validation
- `tests/test_profiler/test_adversarial.py` — 10 adversarial tests
- `src/idse_orchestrator/profiler/README.md` — document schema versioning and hash workflow

**Acceptance:**
- All 10 adversarial tests pass with correct error codes
- Generated ## Agent Profile YAML includes profiler_hash comment
- SessionLoader warns on hash mismatch
- Schema versioning documented with v1.0 → v2.0 migration path
- Error code reference updated with numeric IDs (E1000-E1018, W2001-W2002)

---

### Phase 10.5 — Profiler UX Enhancement (JSON I/O + CLI Refactoring)

**Objective:**
Fix critical UX gap (PFR-2 incomplete): enable users to save/load profiler answers as JSON to support edit-retry workflow when validation fails. Prevent forcing users to restart 20-question intake from scratch when only 1 answer needs correction.

**Problem:**
When profiler validation fails (e.g., E1002 multi_objective_agent on question 3), users must restart the entire 20-question intake. No mechanism exists to save collected answers, edit the failing field, and re-validate. This creates significant UX friction — discovered during manual testing when transformation summary failed validation after completing all 20 questions.

**Solution:**

1. **JSON I/O Functions** (`profiler/cli.py`):
   - `save_profiler_answers_to_json(path, answers)` — serialize answers dict to JSON with sorted keys
   - `load_profiler_answers_from_json(path)` — deserialize JSON, validate schema, return answers dict

2. **CLI Flags** (update `profiler intake` command):
   - `--save-answers <path>` — save collected answers to JSON **before** validation
   - `--from-json <path>` — load answers from JSON, skip interactive prompts, validate and generate spec.md

3. **Edit-Retry Workflow**:
   ```bash
   # First attempt: collect answers, save before validation
   idse profiler intake --save-answers answers.json --spec-out agent.spec.md
   # ❌ Profiler rejected input (E1002 multi_objective_agent)

   # Edit answers.json to fix transformation_summary field
   vim answers.json

   # Retry: load edited JSON, re-validate
   idse profiler intake --from-json answers.json --spec-out agent.spec.md
   # ✅ Profiler accepted, spec.md generated
   ```

4. **CLI Refactoring** (prevent main CLI bloat):
   - Extract profiler command group to `profiler/commands.py`
   - Main `cli.py` imports and registers profiler commands
   - Keeps main CLI under 1800 lines (currently ~1800, would exceed 2000 with JSON I/O additions)

**Components:**

**New Module:** `src/idse_orchestrator/profiler/commands.py`
```python
"""Profiler Click command group."""
import click
from pathlib import Path
from typing import Optional

from .cli import (
    collect_profiler_answers_interactive,
    run_profiler_intake,
    load_profiler_answers_from_json,
    save_profiler_answers_to_json,
)

@click.group()
def profiler():
    """Profiler intake and schema tools."""
    pass

@profiler.command("intake")
@click.option("--from-json", type=click.Path(exists=True, path_type=Path))
@click.option("--save-answers", type=click.Path(path_type=Path))
@click.option("--out", type=click.Path(path_type=Path))
@click.option("--spec-out", type=click.Path(path_type=Path))
def profiler_intake_cmd(...):
    # Phase 1: Intake
    if from_json:
        payload = load_profiler_answers_from_json(from_json)
    else:
        payload = collect_profiler_answers_interactive()
        if save_answers:
            save_profiler_answers_to_json(save_answers, payload)

    # Phase 2: Validation
    result = run_profiler_intake(payload)
    if isinstance(result, ProfilerRejection):
        # Show errors, exit 1
        pass

    # Phase 3: Document Generation
    # ... existing code
```

**Updated Functions in `profiler/cli.py`:**
```python
def save_profiler_answers_to_json(path: Path, payload: Dict[str, Any]) -> None:
    """Save profiler answers to JSON file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")

def load_profiler_answers_from_json(path: Path) -> Dict[str, Any]:
    """Load profiler answers from JSON file."""
    payload = json.loads(path.read_text())
    # Optional: Pydantic pre-validation to catch schema errors early
    try:
        AgentSpecProfilerDoc.model_validate(payload)
    except PydanticValidationError as exc:
        raise click.ClickException(f"Invalid JSON schema: {exc}")
    return payload
```

**Main CLI Update** (`src/idse_orchestrator/cli.py`):
```python
# Remove profiler command definitions (move to profiler/commands.py)
# Add import and registration:
from .profiler.commands import profiler

main.add_command(profiler, name="profiler")
```

**Files:**
- `src/idse_orchestrator/profiler/cli.py` — add JSON save/load functions
- `src/idse_orchestrator/profiler/commands.py` — NEW: profiler Click command group
- `src/idse_orchestrator/cli.py` — update to import profiler commands from profiler/commands.py
- `tests/test_profiler/test_cli_json_io.py` — NEW: test `--save-answers` and `--from-json` workflows
- `src/idse_orchestrator/profiler/README.md` — document JSON I/O workflow

**Tests:**
1. `--save-answers` creates valid JSON file with all 20 answers
2. `--from-json` loads JSON and validates correctly (same result as interactive mode)
3. Edit-retry workflow: save → edit JSON → reload → validate (test with E1002 correction)
4. Main CLI still under 1800 lines after refactoring
5. All existing profiler tests still pass

**Acceptance:**
- `idse profiler intake --save-answers answers.json` creates valid JSON file
- `idse profiler intake --from-json answers.json --spec-out agent.spec.md` generates spec.md without interactive prompts
- Edit-retry workflow documented in README with example
- Profiler command group moved to `profiler/commands.py`
- Main `cli.py` under 1800 lines
- All profiler tests pass (existing + new JSON I/O tests)
