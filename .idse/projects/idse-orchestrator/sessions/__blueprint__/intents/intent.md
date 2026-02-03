# Intent: IDSE Developer Orchestrator

## Why This Product Exists

The IDSE Orchestrator exists to be the **design-time Documentation OS** for Intent-Driven Systems Engineering.

It gives every client repo a predictable, versioned workspace where:

- **Project truth is written down** in IDSE pipeline artifacts
- **Design-time cognition is separated from run-time cognition**
- **Work can be coordinated** across humans and IDE agents (Claude, Codex, etc.)
- **Artifact Core can sync and reason** over a clean IDSE structure

In the broader ecosystem:

- **Artifact Core (Layer 1)** is the multi-tenant backend and global Product Spine host
- **IDSE Orchestrator (Layer 2)** is the per-client, per-repo Documentation OS + coordinator ← THIS PRODUCT
- **IDE Agents (Layer 3)** are the execution helpers that work on the code (Claude Code, GPT Codex, etc.)

This blueprint defines what the Orchestrator must become so that clients can depend on it as stable infrastructure.

## What Success Looks Like

We consider the IDSE Orchestrator successful when:

### Any client repo can run `idse init` and get:
- A valid `.idse/projects/<project>/` workspace
- Sessions with complete IDSE pipelines
- A visible, queryable state of pipeline progression

### The Product Spine for the Orchestrator is reflected in real components:
- **Foundation**: ProjectWorkspace, ConstitutionRules
- **Core Loop**: SessionGraph, PipelineArtifacts, StageStateModel, DocToAgentProfileSpecCompiler
- **Platform**: DesignStore, ArtifactSyncEngine, IDEAgentRouting, AgentRegistry, CLIInterface
- **Validation**: ValidationEngine

### Orchestrator instances can:
- **Sync safely with Artifact Core** (push/pull)
- **Route work to IDE agents** based on `agent_registry.json`
- **Produce AgentProfileSpec** from `spec.md` for downstream runtimes (PromptBraining, Artifact Core)

### CLI is production-ready:
- Installable via `pip install idse-orchestrator`
- Commands available: `init`, `validate`, `status`, `session create/switch`, `spawn`, `compile agent-spec`, `sessions`, `session-info`, `docs install`, `generate-agent-files`
- Constitutional validation detects `[REQUIRES INPUT]` and structural violations
- DesignStore abstraction supports multiple backends (filesystem, Notion, Supabase, Firebase)
- Self-dogfooding: this repo uses its own `.idse/` structure

## Stakeholders

- **IDSE Developer Agency** (maintainer) — owns product vision and constitutional governance
- **Client workspace developers** (users) — consume CLI to manage their IDSE projects
- **IDE agents: Claude Code, GPT Codex** (consumers) — receive agent routing instructions and compiled specs
- **Artifact Core / MCP** (upstream integration) — sync partner for design-time artifacts

## Non-Goals

The Orchestrator **is not**:
- A runtime agent execution engine
- A replacement for PromptBraining
- A generic task management system

It **will not**:
- Directly call LLM models for runtime cognition
- Own long-lived run-time memory (that stays in PromptBraining / Artifact Core)
- Automatically update the Product Spine
- Use global state (all operations are per-workspace, per-repo only)
- Lock into any CMS backend (DesignStore abstraction prevents coupling)
- Infer agent routing via heuristics or LLMs (routing is explicit via registry)

## Constraints

- Python >=3.8
- No runtime LLM calls — deterministic operations only
- Per-workspace, per-repo (no global state)
- CLI-first, CI-friendly
- CMS-agnostic via DesignStore abstraction
- Scriptable for automation/CI pipelines
