# Plan: IDSE Orchestrator SDK

## 1. Phased delivery

### Phase 0 – Repo extraction and scaffolding

- Extract Orchestrator code into its own `idse-orchestrator` repo.
- Establish `.idse/projects/idse-orchestrator/` as the Orchestrator's own IDSE project.
- Capture this blueprint pipeline as the root `__blueprint__` session.

**Exit criteria:**
- Repo exists, installable in editable mode.
- `idse init` works for a simple test project.
- Orchestrator itself is dogfooding its IDSE pipeline.

---

### Phase 1 – MVP Workspace + Pipeline

Scope: `ProjectWorkspace`, `SessionGraph`, `PipelineArtifacts`, `StageStateModel`, `CLIInterface` (core commands).

- Implement:
	- Project creation: `.idse/projects/<project>/`
	- Session creation: `sessions/<session-id>/` with full pipeline structure
	- `CURRENT_SESSION` semantics
	- `session_state.json` with basic stage statuses
	- CLI:
		- `idse init`
		- `idse status`

**Exit criteria:**
- A developer can:
	- Initialize a project
	- See pipeline structure
	- View basic status of each stage

---

### Phase 2 – Governance (Validation + Constitution)

Scope: `ValidationEngine`, `ConstitutionRules`.

- Implement:
	- Core Constitution rules (Articles) as a declarative rule set.
	- `idse validate`:
		- Required pipeline artifacts
		- `[REQUIRES INPUT]` checks
		- Basic structure/ordering rules
	- Integration with `session_state.json.validation_status`.

**Exit criteria:**
- Invalid pipelines are clearly flagged.
- `idse status` shows validation status.
- Constitution rules are versioned and inspectable.

---

### Phase 3 – Agency Sync

Scope: `DesignStore` maturation, `SyncEngine`, `ArtifactConfig`.

- Implement:
	- `DesignStoreFilesystem` as the canonical storage backend.
	- `ArtifactConfig` (config file + env vars).
	- `idse sync push` / `idse sync pull`:
		- Upload/download pipeline artifacts & state.
		- Update `last_sync`.
- Design payload format and minimal sync protocol with Artifact Core.

**Exit criteria:**
- A project's IDSE artifacts can be mirrored into Artifact Core and back.
- Conflicts are at least visible (manual resolution is acceptable for MVP).

---

### Phase 4 – Agent Coordination

Scope: `AgentRegistry`, `IDEAgentRouting`.

- Implement:
	- `agent_registry.json` schema and loader.
	- Routing logic: map stages → agents.
	- CLI helpers (or output in `idse status`) suggesting which agent to use per stage.

**Exit criteria:**
- Team can see "Claude handles intent/context/spec/plan, Codex handles implementation" in status/UI.
- IDE integrations can query which agent to use.

---

### Phase 5 – Doc → AgentProfileSpec compiler

Scope: `DocToAgentProfileSpecCompiler`.

- Implement:
	- `## Agent Profile` YAML block convention in `specs/spec.md`.
	- Compiler that:
		- Reads pipeline spec via `DesignStore`.
		- Builds `AgentProfileSpec` object.
		- Validates and writes spec output file.
	- CLI: `idse compile agent-spec --session <id>`.

**Exit criteria:**
- Given a filled-out `spec.md`, Orchestrator can produce a valid `AgentProfileSpec`.
- PromptBraining / Artifact Core can consume that spec without special casing.

---

## 2. Session strategy

- `__blueprint__` – this document (product-level intent/context/spec/plan/tasks).
- `spine-primitives` – session documenting and evolving the Product Spine entries.
- One session per significant primitive or feature:
	- `session-graph-mvp`
	- `validation-engine-mvp`
	- `sync-engine-mvp`
	- `doc2agentspec-v1`
	- etc.

Each feature session inherits intent/context from the Blueprint and narrows it for that primitive.
