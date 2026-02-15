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
- PromptBraining SDK / Zcompiler — downstream consumer of Orchestrator outputs

## 5. PromptBraining SDK & Zcompiler Relationship

The IDSE Orchestrator produces structured JSON artifacts (AgentProfileSpec, SMART Question specs) that feed the **Zcompiler** — the core of the PromptBraining SDK.

### Zcompiler Role
The Zcompiler is a **deterministic XML transformer**. It converts structured JSON specs into ZPrompt XML artifacts that LLMs execute against. XML is chosen over markdown because agents follow XML instructions with significantly higher adherence and guidance fidelity.

### Pipeline Invariant
Regardless of input type (Agent spec or SMART Question / IDEA Framework), the pipeline is:

```
Structured intake → Validated JSON → Zcompiler → XML artifact → Runtime → Trace → Memory → Next version
```

The *type* of thing being compiled changes. The *pipeline* does not.

### Dual Intake Paths
The Orchestrator's profiler module serves as the **intake bridge** between IDSE and the Zcompiler:

1. **Agent Specs**: Profiler intake (20 questions) → ProfilerDoc → AgentProfileSpec JSON → Zcompiler → Agent XML
2. **SMART Questions / IDEA Frameworks**: (future) Framework intake → structured spec → Zcompiler → Cognitive scaffold XML

Both converge at the Zcompiler's ZPrompt intermediate representation.

### Boundary Contract
- **IDSE Orchestrator** owns: intake, validation, JSON artifact production, pipeline governance
- **Zcompiler** owns: JSON → XML transformation, hashing, versioning, scaffold selection
- **Neither** calls LLMs — deterministic compilation throughout
- **Runtime** (separate) executes the compiled XML against an LLM

### Key Insight
The Zcompiler doesn't just version artifacts for auditing — it **upgrades agent performance** by transforming human-authored structured data into the XML format that LLMs follow most reliably. The compilation *is* the optimization.
