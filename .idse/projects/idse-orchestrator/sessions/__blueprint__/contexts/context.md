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

## 6. The Triangle Architecture (CMSS + XML + Runtime)

Three layers form the complete cognitive infrastructure:

```
[ CMSS (IDSE Orchestrator) ]        ← Authority / governance / versioning
           ↓
[ XML Architecture (Zcompiler) ]    ← Compiled declarative spec (immutable at runtime)
           ↓
[ Execution Runtime (Agency Swarm) ] ← Graph interpreter / tool executor / state logger
```

### Layer Responsibilities

**CMSS (IDSE Orchestrator)** — the control plane:
- Versions agent definitions
- Manages permissions and tool whitelists
- Publishes approved XML
- Enforces governance rules (validation engine, constitution, blueprint claims)
- Activates / deactivates agents
- Handles diffs, rollbacks, audit trails
- Never executes anything

**XML Architecture (Zcompiler output)** — the declarative graph:
- Defines tool surfaces, delegation edges, output schemas, constraints, runtime policies
- Immutable during execution — agents cannot rewrite architecture
- Signed, versioned, deterministic
- Each agent definition is a compiled, hashed artifact

**Execution Runtime (Agency Swarm)** — the execution plane:
- Reads topology from XML (does not decide it)
- Interprets the agent graph
- Executes tools within declared boundaries
- Routes communication between agents
- Logs state via RunTrace
- Does not modify XML or governance state

### Critical Inversion
Agency Swarm stops being "a flexible multi-agent playground" and becomes "a deterministic execution engine that consumes declarative architecture specs." Definition moves upstream to CMSS + Zcompiler. Runtime only interprets.

### Runtime Enforcement (Three Points)

1. **Tool Access**: Instantiated agent receives only tools declared in its XML. No dynamic tool injection.
2. **Delegation**: Agent-to-agent communication validated against XML graph. Undeclared paths are rejected (not warned).
3. **Output Contract**: Every agent output validated against its declared output contract. Invalid shape is rejected, logged, and prevents downstream execution.

### CMSS Implementation (All Three Modes)
- **UI-driven policy manager**: AG-UI front-end (future), Notion as view surface (today)
- **Git-backed architecture repository**: `.idse/` workspace, SHA256 hash chains, blueprint claims
- **Database-driven runtime configuration**: SQLite spine as source of truth, `ArtifactDatabase` CRUD

### Invariant
XML must be signed, versioned, and immutable during execution. Agents cannot rewrite architecture. They can only operate inside it. If this invariant is violated, governance is lost.
