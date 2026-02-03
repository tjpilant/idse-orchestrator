# Spec: IDSE Developer Orchestrator

## 1. Product Scope

The IDSE Orchestrator **MUST**:

- Provide a per-project IDSE workspace rooted at `.idse/projects/<project>/`
- Manage a graph of sessions for each project
- Maintain pipeline artifacts for each session:
  - intent, context, spec, plan, tasks, implementation, feedback
- Track pipeline state (StageStateModel) across sessions
- Enforce IDSE Constitution rules via a ValidationEngine
- Provide a storage abstraction (DesignStore) with at least filesystem support
- Sync artifacts with Agency Core via an AgencySyncEngine
- Coordinate IDE agents via an AgentRegistry and IDEAgentRouting
- Compile `spec.md` → AgentProfileSpec via DocToAgentProfileSpecCompiler
- Expose a coherent CLI interface for all of the above

## 2. Functional Requirements by Spine Primitive

### 2.1 ProjectWorkspace

**MUST** create a project workspace at `.idse/projects/<project>/` with:
- `sessions/`
- `CURRENT_SESSION`
- `session_state.json`

**MUST** ensure `CURRENT_SESSION` always points to a valid session.

**MUST** be agnostic to the rest of the client repo layout.

### 2.2 SessionGraph

**MUST** manage sessions as first-class objects under `sessions/<session-id>/`.

**MUST** support:
- Creating a new session with a full pipeline structure
- Enumerating sessions for status, sync, and UI

**SHOULD** support:
- Special session types (e.g. `__blueprint__`, feature sessions) in later versions

### 2.3 PipelineArtifacts

**MUST** ensure for every session:
- `intent.md`
- `context.md`
- `spec.md`
- `plan.md`
- `tasks.md`
- `implementation/README.md`
- `feedback/feedback.md`

exist (created from templates if needed).

**MUST** treat these as design-time cognition artifacts, not executable code.

### 2.4 StageStateModel

**MUST** maintain `session_state.json` per project with:
- stages map (intent, context, spec, plan, tasks, implementation, feedback)
- `last_sync`
- `validation_status`

**MUST** drive `idse status` output from this model.

### 2.5 ValidationEngine + ConstitutionRules

**MUST** implement `idse validate` which:
- Checks presence of required docs
- Evaluates `[REQUIRES INPUT]` markers
- Applies core Constitution rules (e.g., stage sequence, article compliance)

**MUST** update `validation_status` in `session_state.json`.

**MUST** be driven by a declarative ConstitutionRules set, not hard-coded ad hoc checks.

### 2.6 DesignStore

**MUST** define a storage interface used by core logic:
- `load_session`, `save_session`, `list_sessions`, etc.

**MUST** provide at least `DesignStoreFilesystem` as the default implementation.

**MUST** allow future implementations (Notion, Supabase, Firebase, Obsidian) without changing core logic.

### 2.7 AgencySyncEngine + AgencyConfig

**MUST** implement:
- `idse sync push`
- `idse sync pull`

**MUST** respect configuration from:
- `~/.idseconfig.json`
- Environment variables (`IDSE_AGENCY_URL`, etc.)

**MUST** update `last_sync` in `session_state.json`.

**MUST NOT** auto-change Milestones or Status in the Product Spine.

### 2.8 AgentRegistry + IDEAgentRouting

**MUST** support `agent_registry.json` with entries:
- `id`: agent identifier (e.g. `claude-code`, `gpt-codex`)
- `stages`: which pipeline stages the agent handles

**MUST** provide a way to answer:
- "Which agents handle stage X?"

**SHOULD** be used by commands/UI to suggest which agent to use for which work.

### 2.9 DocToAgentProfileSpecCompiler

**MUST** read `spec.md` for a given session.

**MUST** require a structured `## Agent Profile` YAML block as the canonical input.

**MUST** produce a validated AgentProfileSpec file (YAML/JSON) in a predictable output path.

**MUST** run without calling LLMs or tools.

**MUST NOT** modify Spine; it only outputs specs.

### 2.10 CLIInterface

**MUST** expose at minimum:
- `idse init <project-name>`
- `idse status`
- `idse validate`
- `idse sync push`
- `idse sync pull`

**SHOULD** later expose:
- `idse compile agent-spec --session <id>`
- `idse spawn <session-id>`
- `idse switch <session-id>`

**MUST** return non-zero exit codes on failure and be scriptable.

## 3. Non-Functional Requirements

**Language / runtime:**
- Python 3.x, pip-installable

**Portability:**
- Must work on Linux/macOS dev environments

**Safety:**
- Must not leak client artifacts outside configured Agency Core endpoints
- Must not run unreviewed code or tools by default

**Extensibility:**
- DesignStore is pluggable
- Validation rules can be extended while preserving core rules
- Additional CLI commands can be added without breaking existing ones

## 4. Product Spine Table

| # | Primitive | Module | Area | Layer | Milestone | System Role |
|---|-----------|--------|------|-------|-----------|-------------|
| 1 | ProjectWorkspace | project_workspace.py | Foundation | Workspace | Concept | Primitive |
| 2 | ConstitutionRules | constitution_rules.py | Foundation | Governance | Concept | Primitive |
| 3 | SessionGraph | session_graph.py | Core Loop | Governance | Concept | Primitive |
| 4 | PipelineArtifacts | pipeline_artifacts.py | Core Loop | Artifacts | Concept | Primitive |
| 5 | StageStateModel | stage_state_model.py | Core Loop | Sync | Concept | Primitive |
| 6 | DocToAgentProfileSpecCompiler | compiler/ | Core Loop | Compilation | Concept | Primitive |
| 7 | DesignStore | design_store.py | Platform | Storage | Concept | Primitive |
| 8 | AgencySyncEngine | (TBD) | Platform | Sync | Concept | Primitive |
| 9 | IDEAgentRouting | ide_agent_routing.py | Platform | Coordination | Concept | Primitive |
| 10 | AgentRegistry | agent_registry.py | Platform | Coordination | Concept | Primitive |
| 11 | CLIInterface | cli.py | Platform | CLI | Concept | Primitive |
| 12 | ValidationEngine | validation_engine.py | Validation | Governance | Concept | Primitive |

## 5. Governance Process

1. Each Spine primitive should have at least one IDSE feature session when work is being done on it
2. Status updates are manual: update the Spine table above when a primitive's status changes
3. Milestones are tracked in the blueprint `tasks.md`
4. Validation of Spine coverage: run `idse validate` to check artifact compliance

## 6. Agent Profile

```yaml
id: idse-orchestrator
name: IDSE Developer Orchestrator
description: CLI tool for managing IDSE pipeline artifacts and coordinating IDE agents
goals:
  - Provide deterministic pipeline artifact management
  - Coordinate IDE agent routing
  - Enable CMS-agnostic storage via DesignStore
inputs:
  - User CLI commands
  - Pipeline artifact templates
  - Agent registry configuration
  - Governance rules
outputs:
  - Pipeline artifacts (7 stages)
  - Session state tracking
  - Validation reports
  - Agent profile specs (YAML)
tools:
  - Click CLI framework
  - Jinja2 template engine
  - Pydantic v2 validation
  - PyYAML serialization
constraints:
  - No runtime LLM calls
  - Per-workspace only (no global state)
  - Python >=3.8
  - CLI-first, CI-friendly
memory_policy: {}
runtime_hints: {}
version: "0.1.0"
source_session: __blueprint__
source_blueprint: __blueprint__
```
