# Spec: IDSE Developer Orchestrator

## Product Spine

| # | Primitive | Module | Status | Session |
|---|-----------|--------|--------|---------|
| 1 | ProjectWorkspace | project_workspace.py | Implemented | __blueprint__ |
| 2 | SessionGraph | session_graph.py | Implemented | __blueprint__ |
| 3 | PipelineArtifacts | pipeline_artifacts.py | Implemented | __blueprint__ |
| 4 | StageStateModel | stage_state_model.py | Implemented | __blueprint__ |
| 5 | ValidationEngine | validation_engine.py | Implemented | __blueprint__ |
| 6 | ConstitutionRules | constitution_rules.py | Implemented | __blueprint__ |
| 7 | DesignStore | design_store.py | Defined (not integrated) | __blueprint__ |
| 8 | DesignStoreFilesystem | design_store.py | Defined (not integrated) | __blueprint__ |
| 9 | AgentRegistry | agent_registry.py | Implemented | __blueprint__ |
| 10 | IDEAgentRouting | ide_agent_routing.py | Implemented | __blueprint__ |
| 11 | DocToAgentProfileSpecCompiler | compiler/ | Implemented | __blueprint__ |
| 12 | CLIInterface | cli.py | Implemented | __blueprint__ |

## Primitive Definitions

### ProjectWorkspace
Manages `.idse/projects/<project>/` lifecycle: init, governance files, agent instruction files.

### SessionGraph
Manages session creation, lineage tracking, CURRENT_SESSION pointer, blueprint metadata.

### PipelineArtifacts
Loads and renders Jinja2 templates for the 7-stage pipeline: intent, context, spec, plan, tasks, implementation, feedback.

### StageStateModel
Tracks pipeline stage progression in `session_state.json`. Supports optional DesignStore backend.

### ValidationEngine
Applies ConstitutionRules to pipeline artifacts. Writes validation_status to state.

### ConstitutionRules
Declarative rule definitions: required sections per artifact, pipeline stage list. Exported via `get_rules()`.

### DesignStore
Abstract storage interface (ABC). Methods: `load_artifact`, `save_artifact`, `list_sessions`, `load_state`, `save_state`. CMS-agnostic — never encodes cognition, just moves bytes.

### DesignStoreFilesystem
Default filesystem implementation of DesignStore. Reads/writes `.idse/projects/<project>/` layout.

### AgentRegistry
Manages `agent_registry.json`. Methods: `list_agents`, `get_agent`, `get_agents_for_stage`, `register_agent`. Default agents: claude-code (design stages), gpt-codex (implementation).

### IDEAgentRouting
Routes tasks to IDE agents based on pipeline stage. Uses AgentRegistry for lookup.

### DocToAgentProfileSpecCompiler
Reads `## Agent Profile` YAML from spec.md, merges with blueprint defaults, validates via Pydantic, emits YAML profile. Deterministic — no LLM calls.

### CLIInterface
Click-based CLI with commands: init, validate, status, session create/switch, spawn, compile agent-spec, sessions, session-info, docs install, generate-agent-files.

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
