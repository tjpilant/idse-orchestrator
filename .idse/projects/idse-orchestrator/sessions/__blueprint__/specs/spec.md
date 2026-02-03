# Spec: IDSE Developer Orchestrator

## Product Spine

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

## Primitive Definitions

### ProjectWorkspace (Foundation, Workspace)
The per-project root under `.idse/projects/<project>/` that owns `sessions/`, `CURRENT_SESSION`, and `session_state.json`.

Why primitive: Without it, you don't have a place for IDSE to live in a client repo.

Must do:
- Create the canonical `.idse/projects/<project>/` layout on `idse init`.
- Keep `CURRENT_SESSION` meaningful.

Never does:
- Store reasoning (that's in artifacts),
- Talk to Agency Core directly (that's AgencySyncEngine).

### ConstitutionRules (Foundation, Governance)
The declarative rule set applied by the ValidationEngine (Articles I–X).

Why primitive: Without a formal ruleset, validation is just ad-hoc linting.

Must do:
- Be explicit and inspectable.
- Provide versioned governance (rules can evolve, but are tracked).

Never does:
- Live in code-only "magic"; the Constitution is an artifact, not a vibe.

### SessionGraph (Core Loop, Governance) [MVP]
The model of all sessions in a project and their relationships (root/feature, parent/child).

Why primitive: Orchestrator = "managing sessions over time." The graph is that reality.

Must do:
- Know which sessions exist and their type (blueprint/feature/etc.).
- Support operations like "create new session", "switch session".

Never does:
- Contain the pipeline content; it just references where that content lives.

### PipelineArtifacts (Core Loop, Artifacts)
The canonical set of docs for each session: intent, context, spec, plan, tasks, implementation, feedback.

Why primitive: These are the IDSE artifacts; without them you're not orchestrating anything.

Must do:
- Define filenames/locations (intents/intent.md, specs/spec.md, etc.).
- Guarantee they exist (even as templates) when a session is created.

Never does:
- Decide meaning or status; it's content-only.
- Execute tasks; it only describes them.

### StageStateModel (Core Loop, Sync)
The structured representation of pipeline stage state stored in `session_state.json`.

Why primitive: This is how the Orchestrator knows where the pipeline is.

Must do:
- Track per-stage state.
- Track last_sync, validation_status.

Never does:
- Contain reasoning; it's just state.
- Trigger work automatically (no side-effectful state changes).

### DocToAgentProfileSpecCompiler (Core Loop, Compilation)
The design-time compiler that turns structured spec.md (e.g. ## Agent Profile YAML) into a machine-readable AgentProfileSpec.

Why primitive: This is the formal boundary from IDSE to runtime cognition (PromptBraining, Agency Core).

Must do:
- Read spec.md via DesignStore.
- Parse the dedicated structured section.
- Validate and emit AgentProfileSpec.

Never does:
- Call models or tools.
- Auto-modify Spine or pipeline docs.

### DesignStore (Platform, Storage)
The abstract storage interface for reading/writing projects & sessions, implemented at least by a filesystem backend.

Why primitive: This is how Orchestrator becomes CMS-agnostic (filesystem, Notion, Supabase, Firebase...).

Must do:
- Provide load_session, save_session, list_sessions, etc.
- Be the only way core logic touches storage.

Never does:
- Encode cognition; it just moves bytes around.
- Contain product logic (no validation or compilation here).

### AgencySyncEngine (Platform, Sync)
The mechanism that syncs artifacts between local .idse and Agency Core / MCP.

Why primitive: Layer 2 must be tied to Layer 1; otherwise this is just a local note-taker.

Must do:
- Implement push/pull of artifacts.
- Update StageStateModel.last_sync.
- Respect AgencyConfig.

Never does:
- Infer milestones or statuses automatically.
- Run runtime cognition (no model calls here).

### IDEAgentRouting (Platform, Coordination)
The logic that uses AgentRegistry to decide which agent to suggest/invoke for a given stage or operation.

Why primitive: Without routing logic, the registry is just static config.

Must do:
- Provide simple APIs like get_agents_for_stage("implementation").
- Drive hints / handoff context to IDE environments.

Never does:
- Decide architecture or modify docs; it just routes.

### AgentRegistry (Platform, Coordination)
The mapping of pipeline stages to IDE agents stored in agent_registry.json.

Why primitive: This is the contract between Orchestrator and IDE tools.

Must do:
- Define schema for agent entries (id, stages, etc.).
- Answer: "Which agent(s) are responsible for stage X?"

Never does:
- Execute agents itself.
- Contain task lists (that's Tasks layer).

### CLIInterface (Platform, CLI)
The command-line surface (idse init/status/validate/sync/...) over all the other primitives.

Why primitive: Without a CLI, the Orchestrator doesn't orchestrate; it's just a library.

Must do:
- Expose core operations (init, status, validate, sync, compile) in a predictable way.
- Map user intent to primitives without adding secret logic.

Never does:
- Contain business rules that aren't in the primitives.
- Maintain its own state separate from ProjectWorkspace / StageStateModel.

### ValidationEngine (Validation, Governance)
The subsystem that runs constitutional / structural checks over pipeline artifacts.

Why primitive: It enforces "IDSE Constitution compliance" at design time.

Must do:
- Check required sections.
- Detect [REQUIRES INPUT].
- Encode basic rules like stage sequencing.

Never does:
- Mutate Spine entries.
- Decide milestones; it just reports quality/validity.

## Derived Components (Not Primitives)

### DesignStoreFilesystem
Concrete filesystem implementation of DesignStore. Reads/writes `.idse/projects/<project>/` layout.

### Sync helpers (DesignStoreFilesystem)
DesignStoreFilesystem provides push/pull helpers for pipeline artifacts and relies on StageStateModel to track last_sync. Not primitives.

## Governance Process

1. Each Spine primitive should have at least one IDSE feature session when work is being done on it
2. Status updates are manual: update the Spine table above when a primitive's status changes
3. Milestones are tracked in the blueprint `tasks.md`
4. Validation of Spine coverage: run `idse validate` to check artifact compliance

## Agent Profile

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
