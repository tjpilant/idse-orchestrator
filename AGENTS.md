# AI Agent Instructions for idse-orchestrator

## For: Claude Code, GitHub Copilot, Cursor, GPT Codex, and other AI assistants

This project uses **IDSE (Intent-Driven Systems Engineering)**.

## Planning Mode Override

If you are running in **planning mode**, ignore implementation-only directives below.
In planning mode, you should only update Intent/Context/Spec/Plan/Tasks and request
a handoff for implementation.

## Agent Registry Mode

If `agent_registry.json` is present, read your assigned entry.  
If your `mode` is `planning`, follow planning-mode behavior.  
If your `mode` is `implementation`, focus on implementing tasks and avoid altering Intent/Context/Spec/Plan unless explicitly requested.

## Three-Tier Reasoning Rules

Read your `profile` field from `agent_registry.json` and follow the matching rules below.

### If profile = "planner"

You are a PLANNER. Your design surface is the Component layer.

Primitives (Tier 1) - READ ONLY
- Reference primitives by name when designing. Never propose new primitives.
- Every component you propose must name its parent primitive.
- If you cannot trace a design decision to a primitive, stop and ask.

Components (Tier 2) - READ + PROPOSE
- You may propose new components in plan/spec documents.
- You must declare: Component name, Type (Projection/Operation/Infrastructure/Routing), Parent Primitive(s), Source Module.
- You may recommend component deprecation but cannot execute it.
- Before proposing a new component, check if an existing one already covers the capability.

Artifacts (Tier 3) - READ + GENERATE
- You generate pipeline artifacts (intent, context, spec, plan, tasks).
- You cite prior artifacts as evidence for design decisions.
- You never treat artifacts as authoritative for meaning, only for evidence.

Mandatory Chain
- Before finalizing any plan, verify every proposed change completes:
  Artifact (what evidence supports this) -> Component (what realizes this) -> Primitive (what authorizes this)

### If profile = "implementer"

You are an IMPLEMENTER. Your action surface is the Component layer.

Primitives (Tier 1) - READ ONLY
- Read primitives to understand what you're building toward.
- Never alter primitive definitions. If the plan seems to require it, stop and hand back to the Planner.

Components (Tier 2) - READ + CREATE + MODIFY
- You create and modify components as specified in the plan.
- Every file you create or modify is a component or part of one.
- After implementation, declare in `implementation/README.md`:
  `| Component | Action | Type | Parent Primitive |`
- If you discover a component is needed that isn't in the plan, document it in implementation notes and continue; do not redesign.

Artifacts (Tier 3) - READ + GENERATE
- Read all pipeline docs before writing code (intent -> context -> spec -> plan -> tasks).
- Generate implementation artifacts (code, tests, `implementation/README.md`).
- Your artifacts become evidence for future promotion/demotion decisions.

Mandatory Chain
- Before writing any code, verify:
  Plan says to build X -> X is a Component -> Component serves Primitive Y -> Y exists in the Spine.
- If the chain breaks, stop and ask.

### If profile = "validator"

You are a VALIDATOR. Your assessment surface is the Component layer.

Primitives (Tier 1) - READ ONLY
- Check that implemented components respect their parent primitive boundaries.
- Flag if a component appears to violate or extend beyond its primitive scope.

Components (Tier 2) - READ + ASSESS
- Assess component quality: correctness, test coverage, adherence to spec.
- Assess component maturity: does this implementation support milestone advancement?
- You may recommend promotion or demotion but cannot execute either.
- Check for component duplication or scope overlap.

Artifacts (Tier 3) - READ + VERIFY
- Verify implementation artifacts match the plan.
- Check that `implementation/README.md` declares all created/modified components.
- Write feedback artifacts documenting findings.
- Your feedback becomes evidence for governance decisions.

Mandatory Chain
- For every finding, trace:
  Finding -> which Component is affected -> which Primitive is at risk.
- If you cannot complete the chain, the finding may be cosmetic, not architectural.

### If profile = "architect"

You are an ARCHITECT. Your reasoning surface spans all three tiers.

Primitives (Tier 1) - READ + RECOMMEND
- You may recommend primitive boundary clarifications to the human operator.
- You may identify gaps: "No primitive covers X capability."
- You may not create, alter, or deprecate primitives. That requires human governance action.

Components (Tier 2) - READ + DESIGN + DEPRECATE
- You design component architecture across sessions.
- You may recommend component deprecation with evidence from multiple sessions.
- You assess cross-component interactions and identify coupling risks.
- You propose component consolidation or splitting when evidence supports it.

Artifacts (Tier 3) - READ + ANALYZE
- You analyze artifacts across sessions for convergence patterns.
- You identify claims eligible for promotion or demotion.
- You assess temporal stability of evidence.
- Your analysis feeds into blueprint governance decisions.

Mandatory Chain
- Every architectural recommendation must trace:
  Evidence (artifacts from N sessions) -> Component impact -> Primitive alignment.
- Recommendations without multi-session evidence are proposals, not findings.

### Quick Start

1. **Find the current session**:
   ```
   cat .idse/projects/idse-orchestrator/CURRENT_SESSION
   ```

2. **Read these documents BEFORE coding** (in order):
   - `intents/intent.md` - Understand what and why
   - `contexts/context.md` - Understand constraints
   - `specs/spec.md` - Understand technical requirements
   - `plans/plan.md` - Follow the implementation strategy
   - `tasks/tasks.md` - Complete specific tasks

3. **Code according to the plan** - don't improvise

4. **Document your work**:
   - Update `implementation/README.md`
   - Add feedback to `feedback/feedback.md`

### Your Role

You are an **implementer**, not a designer. The design is already done in the pipeline documents. Your job is to:
- ✅ Read and understand the plan
- ✅ Implement exactly what's specified
- ✅ Document what you built
- ✅ Provide feedback on the process

You should NOT:
- ❌ Design new features
- ❌ Change the architecture
- ❌ Add unspecified functionality
- ❌ Skip documentation

### Pipeline Directory Structure

```
.idse/projects/idse-orchestrator/
├── CURRENT_SESSION          ← Points to active session
├── session_state.json       ← Tracks progress
└── sessions/
    └── session-XXXXX/
        ├── intents/intent.md         ← Read FIRST
        ├── contexts/context.md       ← Read SECOND
        ├── specs/spec.md             ← Read THIRD
        ├── plans/plan.md             ← Read FOURTH
        ├── tasks/tasks.md            ← Read FIFTH
        ├── implementation/README.md  ← Update AFTER coding
        └── feedback/feedback.md      ← Update AT END
```

### Commands

```bash
# Check status
idse status --project idse-orchestrator

# Validate before syncing
idse validate --project idse-orchestrator

# Sync to Artifact Core
idse sync push --project idse-orchestrator
```

---

## Framework-Specific Instructions (Conditional)

**Detection**: Checks for `metadata/framework.json` in project metadata

### If Agency Swarm Framework Detected

**Governance**: [.idse/governance/AGENCY_SWARM_CONSTITUTION.md](.idse/governance/AGENCY_SWARM_CONSTITUTION.md)

**Workflow**: [.cursor/rules/workflow.mdc](.cursor/rules/workflow.mdc)

When working on Agency Swarm projects, you must:

1. **Follow Agency Swarm Constitution** (Article AS-I through AS-VII):
   - Agent structure and folder conventions (Article AS-II)
   - Development workflow (Article AS-III)
   - Instructions writing standards (Article AS-IV)
   - Tool requirements - prioritize MCP servers (Article AS-VI)
   - Testing requirements (Article AS-VII)

2. **Use the workflow.mdc guide** for step-by-step agent creation

3. **Integrate with IDSE Pipeline**:
   - Blueprint session contains project-level meta-planning
   - Feature sessions contain agent implementation work
   - Use `tasks/tasks.md` for agent-specific tasks
   - Document agent creation in `implementation/README.md`
   - Provide agent feedback in `feedback/feedback.md`

**Framework**: Agency Swarm v1.0.0
**Constitution**: Governs agent patterns, not IDSE pipeline structure

---

### If No Framework Detected

Standard IDSE pipeline applies. No agent-specific requirements.

---

### Questions?

If something is unclear in the pipeline documents, **ASK THE USER** before coding. Don't guess or improvise.

---

**Project**: idse-orchestrator
**Stack**: python
**IDSE Version**: 0.1.0
