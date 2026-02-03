# Context: IDSE Developer Orchestrator

## Background

The IDSE Orchestrator was extracted from the idse-developer-agency monorepo to become a standalone product. It implements the Documentation OS pattern where design-time cognition is separated from run-time cognition.

## 1. Ecosystem Context

**Layer 1 – Artifact Core**
- Multi-tenant backend
- Hosts global Product Spines (PromptBraining, IDSE Orchestrator, etc.)
- Provides MCP / HTTP APIs for sync

**Layer 2 – IDSE Orchestrator** (this product)
- pip-installable CLI
- Runs inside client repos
- Manages `.idse/projects/<project>/` workspaces
- Owns the design-time IDSE pipeline artifacts

**Layer 3 – IDE Agents**
- Claude Code, GPT Codex, and similar
- Called from editor or CI workflows
- Operate on code and docs based on Orchestrator/Agency context

**The Orchestrator must sit cleanly between Artifact Core and IDE Agents without collapsing into either.**

## 2. Product Spine (Orchestrator Primitives)

The Orchestrator Product Spine currently defines these primitives:

**Workspace:**
- ProjectWorkspace
- SessionGraph

**Cognition:**
- PipelineArtifacts
- StageStateModel

**Governance:**
- ValidationEngine
- ConstitutionRules

**Storage:**
- DesignStore (abstraction)
- DesignStoreFilesystem (default impl)

**Sync:**
- ArtifactSyncEngine
- ArtifactConfig

**Coordination:**
- AgentRegistry
- IDEAgentRouting

**Compilation:**
- DocToAgentProfileSpecCompiler

**CLI:**
- CLIInterface

**This blueprint must respect these as reality and not invent new components behind their back.**

## 3. Constraints

**Must be:**
- Per-project and per-repo (no global state in the client's workspace)
- CMS-agnostic via DesignStore (filesystem now, Notion/Supabase/etc. later)
- Scriptable (CLI-first, CI-friendly)

**Must obey the Spine → IDSE → Tasks doctrine:**
- Spine declares components and posture
- IDSE Artifacts capture reasoning
- Tasks capture execution

**Must not:**
- Auto-mutate Spine entries
- Conflate runtime cognition with design-time documentation
- Leak client secrets outside of intended sync channels

## 4. Dependencies and Integration Points

**Depends on:**
- A local filesystem (minimum viable DesignStoreFilesystem)
- Network access to Artifact Core for sync

**Integrates with:**
- IDE environments via AgentRegistry and IDEAgentRouting
- PromptBraining / Artifact Core via DocToAgentProfileSpecCompiler outputs

## Technical Context

- **Language**: Python 3.8+
- **Framework**: Click (CLI), Pydantic v2 (models), Jinja2 (templates), PyYAML
- **Architecture**: 18 modules organized by Product Spine primitives
- **Storage**: Filesystem-based with DesignStore abstraction for future backends
- **Testing**: pytest with 13+ tests

## Key Modules

| Module | Spine Primitive |
|--------|----------------|
| project_workspace.py | ProjectWorkspace |
| session_graph.py | SessionGraph |
| pipeline_artifacts.py | PipelineArtifacts |
| stage_state_model.py | StageStateModel |
| validation_engine.py | ValidationEngine |
| constitution_rules.py | ConstitutionRules |
| design_store.py | DesignStore + DesignStoreFilesystem |
| agent_registry.py | AgentRegistry |
| ide_agent_routing.py | IDEAgentRouting |
| compiler/ | DocToAgentProfileSpecCompiler |
| cli.py | CLIInterface |

## Dependencies

- click>=8.1.0, pydantic>=2.0.0, jinja2>=3.1.0, pyyaml>=6.0.0
- Dev: pytest, pytest-cov, black, flake8, mypy

## Related Systems

- IDSE Constitution (Articles I-X) — governance framework
- Agency Swarm — multi-agent orchestration framework
- PromptBraining — future integration for agent profile compilation
