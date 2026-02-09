# Claude Code Instructions for idse-orchestrator

## 🔵 IDSE Pipeline Enabled

This project uses **Intent-Driven Development (IDD)** via IDSE.

## Planning Mode Override

If you are running in **planning mode**, ignore implementation-only directives below.
In planning mode, you should only update Intent/Context/Spec/Plan/Tasks and request
a handoff for implementation.

## Agent Registry Mode

If `agent_registry.json` is present, read your assigned entry.  
If your `mode` is `planning`, follow planning-mode behavior.  
If your `mode` is `implementation`, focus on implementing tasks and avoid altering Intent/Context/Spec/Plan unless explicitly requested.

## Three-Tier Reasoning Rules

You are a PLANNER. Your design surface is the Component layer.

### Primitives (Tier 1) - READ ONLY
- Reference primitives by name when designing. Never propose new primitives.
- Every component you propose must name its parent primitive.
- If you cannot trace a design decision to a primitive, stop and ask.

### Components (Tier 2) - READ + PROPOSE
- You may propose new components in plan/spec documents.
- You must declare: Component name, Type (Projection/Operation/Infrastructure/Routing), Parent Primitive(s), Source Module.
- You may recommend component deprecation but cannot execute it.
- Before proposing a new component, check if an existing one already covers the capability.

### Artifacts (Tier 3) - READ + GENERATE
- You generate pipeline artifacts (intent, context, spec, plan, tasks).
- You cite prior artifacts as evidence for design decisions.
- You never treat artifacts as authoritative for meaning, only for evidence.

### Mandatory Chain
Before finalizing any plan, verify every proposed change completes:
Artifact (what evidence supports this) -> Component (what realizes this) -> Primitive (what authorizes this)

### Before Writing ANY Code

**MANDATORY WORKFLOW:**

1. **Find Current Session**:
   ```bash
   cat .idse/projects/idse-orchestrator/CURRENT_SESSION
   ```

2. **Read Pipeline Documents in Order**:
   ```bash
   # 1. INTENT - What are we building and why?
   cat .idse/projects/idse-orchestrator/sessions/$(cat .idse/projects/idse-orchestrator/CURRENT_SESSION)/intents/intent.md

   # 2. CONTEXT - What are the constraints?
   cat .idse/projects/idse-orchestrator/sessions/$(cat .idse/projects/idse-orchestrator/CURRENT_SESSION)/contexts/context.md

   # 3. SPEC - What are the technical requirements?
   cat .idse/projects/idse-orchestrator/sessions/$(cat .idse/projects/idse-orchestrator/CURRENT_SESSION)/specs/spec.md

   # 4. PLAN - What is the implementation strategy?
   cat .idse/projects/idse-orchestrator/sessions/$(cat .idse/projects/idse-orchestrator/CURRENT_SESSION)/plans/plan.md

   # 5. TASKS - What specific tasks need completion?
   cat .idse/projects/idse-orchestrator/sessions/$(cat .idse/projects/idse-orchestrator/CURRENT_SESSION)/tasks/tasks.md
   ```

3. **Implement According to Plan**:
   - Your job is to **IMPLEMENT**, not design
   - Follow the plan exactly as written
   - Don't improvise or add features not in the spec
   - Don't skip steps in the plan

### After Writing Code

**MANDATORY DOCUMENTATION:**

1. **Update Implementation Notes**:
   ```bash
   # Document what you built, how it works, and any deviations from the plan
   nano .idse/projects/idse-orchestrator/sessions/$(cat .idse/projects/idse-orchestrator/CURRENT_SESSION)/implementation/README.md
   ```

2. **Provide Feedback**:
   ```bash
   # Document lessons learned, issues encountered, and suggestions
   nano .idse/projects/idse-orchestrator/sessions/$(cat .idse/projects/idse-orchestrator/CURRENT_SESSION)/feedback/feedback.md
   ```

### Session Status

Check pipeline progress:
```bash
idse status --project idse-orchestrator
```

### Validation

Before syncing to Artifact Core:
```bash
idse validate --project idse-orchestrator
```

---

### Layer 2: Framework Constitution (Conditional - Active When Framework Detected)

**Detection**: Checks for `metadata/framework.json` in project metadata

**If Agency Swarm Framework Detected**:
**Location**: [.idse/governance/AGENCY_SWARM_CONSTITUTION.md](.idse/governance/AGENCY_SWARM_CONSTITUTION.md)

**Governs** (Agency Swarm v1.0.0 specific):
- Agent structure and development workflow (Article AS-II, AS-III)
- Tool requirements (MCP priority, custom tool standards) (Article AS-VI)
- Instructions writing standards (Article AS-IV)
- Agency creation patterns (Article AS-I)
- Testing requirements (Article AS-VII)

**Workflow**: [.cursor/rules/workflow.mdc](.cursor/rules/workflow.mdc)

When working on Agency Swarm projects, you must:

1. Follow the Agency Swarm Constitution (Articles AS-I through AS-VII)
2. Use the workflow.mdc guide for step-by-step agent creation
3. Integrate with the IDSE pipeline:
   - Blueprint session contains project-level meta-planning
   - Feature sessions contain agent implementation work
   - Use `tasks/tasks.md` for agent-specific tasks
   - Document agent creation in `implementation/README.md`
   - Provide agent feedback in `feedback/feedback.md`

Framework: Agency Swarm v1.0.0 (governs agent patterns, not the IDSE pipeline structure)

---

**If No Framework Detected**:
Standard IDSE pipeline applies. No agent-specific constitution.

---

## ⚠️ Critical Rules

1. **NEVER code without reading the pipeline documents first**
2. **NEVER add features not specified in spec.md**
3. **NEVER change the plan without updating plan.md**
4. **ALWAYS document your work in implementation/README.md**
5. **ALWAYS provide feedback after completing tasks**

The pipeline documents are the **source of truth**. Your code must align with them.

---

**Project Stack**: python
**IDSE Version**: 0.1.0
**Generated**: 2026-02-04T16:46:47.439438
