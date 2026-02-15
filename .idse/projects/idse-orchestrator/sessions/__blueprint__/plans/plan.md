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

---

## Appendix A: Zcompiler v1 — AgentSpec Compilation Path

### Role
The AgentSpec compilation path transforms a validated `AgentProfileSpec` (JSON) into a deterministic, versioned `AgentArtifact` (ZPrompt XML) that can be loaded by `AgentRuntime`, traced by `RunTrace`, and versioned by `ArtifactRegistry`.

### Input: AgentProfileSpec

```
AgentProfileSpec {
  name                    // nullable — assigned post-compilation or by registry
  description             // from transformation_summary
  objective_function {
    input_description
    output_description
    transformation_summary
  }
  success_criteria
  out_of_scope[]
  capabilities[] { task, method }   // max 8
  action_permissions { may[], may_not[] }
  constraints[]
  failure_modes[]
  output_contract {
    format_type             // "narrative" | "json" | "hybrid"
    required_sections[]
    required_metadata[]
    validation_rules[]
  }
  persona {
    industry_context, tone, detail_level
    reference_preferences[], communication_rules[]
  }
}
```

### Output: AgentArtifact

```
AgentArtifact {
  id
  sourceSpecHash         // SHA256 of input AgentProfileSpec
  zpromptXml             // fully resolved ZPrompt XML document
  modelTarget
  compileHash            // SHA256 of all compilation inputs + version
  compilerVersion
  createdAt
}
```

No optional fields. No partial artifacts. No side effects.

### ZPrompt IR (Internal Representation)

```
ZPrompt {
  mission { objective, successCriteria, exclusions[] }
  role { permissions[], prohibitions[], constraints[], failureConditions[] }
  taskPolicy { tasks[] { name, method } }
  outputContract { formatType, sections[], metadata[], validationRules[] }
  persona { industry, tone, detailLevel, references[], communicationRules[] }
  modelTarget
}
```

Every field traces back to an `AgentProfileSpec` field. No inference. No generation.

### 10-Stage Compilation Pipeline

| Stage | Input | Output | Logic |
|-------|-------|--------|-------|
| 1. Mission Extraction | objective_function + success_criteria + out_of_scope | mission IR | Direct mapping |
| 2. Role Binding | action_permissions + constraints + failure_modes | role IR | Explicit (not inferred like SQRA) |
| 3. Task Policy Assembly | capabilities[] | taskPolicy IR | Direct mapping (max 8, pre-validated) |
| 4. Output Contract Binding | output_contract | outputContract IR | Direct mapping |
| 5. Persona Overlay | persona | persona IR | Nullable fields omitted from XML |
| 6. Model Target Selection | CompilerConfig + task complexity | modelTarget | Deterministic heuristic |
| 7. ZPrompt Assembly | All IR sections | Complete ZPrompt | Composition only |
| 8. XML Materialization | ZPrompt IR | XML document | Template rendering, 1:1 field mapping |
| 9. Hash & Version | AgentProfileSpec + modelTarget + version | sourceSpecHash + compileHash | SHA256 |
| 10. Emit AgentArtifact | All above | Final immutable artifact | No side effects |

### XML Output Structure

```xml
<agent version="1.0" compiler="zcompiler-v1">
  <mission>
    <objective>
      <input>...</input>
      <output>...</output>
      <transform>...</transform>
    </objective>
    <success-criteria>...</success-criteria>
    <exclusions><exclusion>...</exclusion></exclusions>
  </mission>
  <role>
    <permissions><permission>...</permission></permissions>
    <prohibitions><prohibition>...</prohibition></prohibitions>
    <constraints><constraint>...</constraint></constraints>
    <failure-conditions><condition>...</condition></failure-conditions>
  </role>
  <task-policy>
    <task name="..."><method>...</method></task>
  </task-policy>
  <output-contract format="...">
    <sections><section>...</section></sections>
    <metadata><field>...</field></metadata>
    <validation><rule>...</rule></validation>
  </output-contract>
  <persona industry="..." tone="..." detail="...">
    <references><ref>...</ref></references>
    <communication-rules><rule>...</rule></communication-rules>
  </persona>
</agent>
```

### Hash Chain: Full Traceability

```
Profiler intake (20 Qs)
  → profiler_hash (SHA256 of ProfilerDoc JSON)
    → AgentProfileSpec JSON
      → sourceSpecHash (SHA256 of spec)
        → Zcompiler stages 1-8
          → compileHash (SHA256 of sourceSpecHash + modelTarget + version)
            → AgentArtifact (immutable, versioned)
```

### Difference from SMART Question Path

| Concern | SMART Question | Agent Spec |
|---------|---------------|------------|
| Input | SmartQuestion + UserBlueprint | AgentProfileSpec |
| Role source | Inferred from SQRA role enum | Explicit from action_permissions |
| Scaffold | Selected (IDEA/Blueprint/TradeoffMatrix) | Fixed: Agent XML template |
| Task policy | None (single question) | Explicit capabilities[] (max 8) |
| Guardrails | Minimal (role-scoped) | Full (may/may_not/constraints/failure_modes) |

Both converge at ZPrompt IR. Both emit through the same hashing and versioning stages.

### v1 Non-Goals
- Does not optimize or rewrite XML
- Does not learn from execution results
- Does not resolve CMS/database SOPs (that's runtime)
- Does not inject tool definitions (that's runtime configuration)
- Does not call LLMs for any reason
