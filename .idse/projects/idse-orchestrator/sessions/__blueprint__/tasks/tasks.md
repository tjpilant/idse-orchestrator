# Tasks: IDSE Orchestrator SDK

> These are Blueprint-level tasks (epics). Each should spawn its own feature session with a more detailed task breakdown.

## 1. Repo & self-dogfooding

- [ ] Create `idse-orchestrator` repo and migrate existing orchestrator code.
- [ ] Initialize `.idse/projects/idse-orchestrator/` with a `__blueprint__` session.
- [ ] Save this Blueprint pipeline into the `__blueprint__` session.
- [ ] Document how to run `idse` inside this repo for self-dogfooding.

## 2. Phase 1 – Workspace + Pipeline

- [ ] Implement `ProjectWorkspace` for `.idse/projects/<project>/` layout.
- [ ] Implement `SessionGraph` with creation + listing.
- [ ] Implement `PipelineArtifacts` generation (intents/contexts/specs/plans/tasks/...).
- [ ] Implement `StageStateModel` + `session_state.json` wiring.
- [ ] Implement `CLIInterface` commands:
	- [ ] `idse init <project>`
	- [ ] `idse status`

## 3. Phase 2 – Governance

- [ ] Define `ConstitutionRules` as a declarative rule set.
- [ ] Implement `ValidationEngine` to apply rules to pipeline artifacts.
- [ ] Wire `idse validate` → `ValidationEngine` → `session_state.json.validation_status`.
- [ ] Update `idse status` to show validation status.

## 4. Phase 3 – Sync

- [ ] Finalize `DesignStore` interface and `DesignStoreFilesystem` implementation.
- [ ] Implement `AgencyConfig` (config file + env vars).
- [ ] Implement `SyncEngine`:
	- [ ] `idse sync push`
	- [ ] `idse sync pull`
- [ ] Define and document the sync payload schema with Agency Core.

## 5. Phase 4 – Agent Coordination

- [ ] Define `agent_registry.json` schema.
- [ ] Implement `AgentRegistry` loader and validation.
- [ ] Implement `IDEAgentRouting` helpers (e.g., `get_agents_for_stage(stage)`).
- [ ] Update `idse status` (or a dedicated command) to show per-stage agent suggestions.

## 6. Phase 5 – Doc → AgentProfileSpec compiler

- [ ] Define `AgentProfileSpec` schema (shared or local) for IDSE.
- [ ] Define `## Agent Profile` YAML structure in `specs/spec.md` templates.
- [ ] Implement `DocToAgentProfileSpecCompiler`:
	- [ ] Read `specs/spec.md` via `DesignStore`.
	- [ ] Parse YAML block → `AgentProfileSpec`.
	- [ ] Validate and write out spec file.
- [ ] Implement `idse compile agent-spec --session <id>` CLI command.
- [ ] Document integration with PromptBraining / Agency Core.

## 7. Governance & Spine alignment

- [ ] Create an `idse-orchestrator` Product Spine table listing all primitives.
- [ ] Ensure each primitive has:
	- [ ] At least one IDSE feature session
	- [ ] Linked Blueprint tasks
- [ ] Define a process for manually updating Milestones and Status for Orchestrator Spine entries based on lifecycle IDSE artifacts.
