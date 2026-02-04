# Tasks: IDSE Orchestrator SDK

> These are Blueprint-level tasks (epics). Each should spawn its own feature session with a more detailed task breakdown.

## 1. Repo & self-dogfooding

- [x] Create `idse-orchestrator` repo and migrate existing orchestrator code.
- [x] Initialize `.idse/projects/idse-orchestrator/` with a `__blueprint__` session.
- [x] Save this Blueprint pipeline into the `__blueprint__` session.
- [x] Document how to run `idse` inside this repo for self-dogfooding.

## 2. Phase 1 – Workspace + Pipeline

- [x] Implement `ProjectWorkspace` for `.idse/projects/<project>/` layout.
- [x] Implement `SessionGraph` with creation + listing.
- [x] Implement `PipelineArtifacts` generation (intents/contexts/specs/plans/tasks/...).
- [x] Implement `StageStateModel` + `session_state.json` wiring.
- [x] Implement `CLIInterface` commands:
	- [x] `idse init <project>`
	- [x] `idse status`

## 3. Phase 2 – Governance

- [x] Define `ConstitutionRules` as a declarative rule set.
- [x] Implement `ValidationEngine` to apply rules to pipeline artifacts.
- [x] Wire `idse validate` → `ValidationEngine` → `session_state.json.validation_status`.
- [x] Update `idse status` to show validation status.

## 4. Phase 3 – Sync

- [x] Finalize `DesignStore` interface and `DesignStoreFilesystem` implementation.
- [x] Implement `ArtifactConfig` (config file + env vars).
- [x] Implement sync CLI:
	- [x] `idse sync push`
	- [x] `idse sync pull`
	- [x] `idse sync test`
	- [x] `idse sync tools`
	- [x] `idse sync describe`
- [x] Document Notion MCP backend setup and payload expectations.
- [ ] Add Supabase DesignStore backend (future).

## 5. Phase 4 – Agent Coordination

- [x] Define `agent_registry.json` schema.
- [x] Implement `AgentRegistry` loader and validation.
- [x] Implement `IDEAgentRouting` helpers (e.g., `get_agents_for_stage(stage)`).
- [x] Update `idse status` (or a dedicated command) to show per-stage agent suggestions.

## 6. Phase 5 – Doc → AgentProfileSpec compiler

- [x] Define `AgentProfileSpec` schema (shared or local) for IDSE.
- [x] Define `## Agent Profile` YAML structure in `specs/spec.md` templates.
- [x] Implement `DocToAgentProfileSpecCompiler`:
	- [x] Read `specs/spec.md` via `DesignStore`.
	- [x] Parse YAML block → `AgentProfileSpec`.
	- [x] Validate and write out spec file.
- [x] Implement `idse compile agent-spec --session <id>` CLI command.
- [x] Document integration with PromptBraining / Artifact Core.

## 7. Governance & Spine alignment

- [x] Create an `idse-orchestrator` Product Spine table listing all primitives.
- [x] Ensure each primitive has:
	- [x] At least one IDSE feature session
	- [x] Linked Blueprint tasks
- [x] Define a process for manually updating Milestones and Status for Orchestrator Spine entries based on lifecycle IDSE artifacts.
