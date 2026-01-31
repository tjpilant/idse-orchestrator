# Claude Code Instructions for {project_name}

## 🔵 IDSE Pipeline Enabled

This project uses **Intent-Driven Development (IDD)** via IDSE.

### Before Writing ANY Code

**MANDATORY WORKFLOW:**

1. **Find Current Session**:
   ```bash
   cat .idse/projects/{project_name}/CURRENT_SESSION
   ```

2. **Read Pipeline Documents in Order**:
   ```bash
   # 1. INTENT - What are we building and why?
   cat .idse/projects/{project_name}/sessions/$(cat .idse/projects/{project_name}/CURRENT_SESSION)/intents/intent.md

   # 2. CONTEXT - What are the constraints?
   cat .idse/projects/{project_name}/sessions/$(cat .idse/projects/{project_name}/CURRENT_SESSION)/contexts/context.md

   # 3. SPEC - What are the technical requirements?
   cat .idse/projects/{project_name}/sessions/$(cat .idse/projects/{project_name}/CURRENT_SESSION)/specs/spec.md

   # 4. PLAN - What is the implementation strategy?
   cat .idse/projects/{project_name}/sessions/$(cat .idse/projects/{project_name}/CURRENT_SESSION)/plans/plan.md

   # 5. TASKS - What specific tasks need completion?
   cat .idse/projects/{project_name}/sessions/$(cat .idse/projects/{project_name}/CURRENT_SESSION)/tasks/tasks.md
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
   nano .idse/projects/{project_name}/sessions/$(cat .idse/projects/{project_name}/CURRENT_SESSION)/implementation/README.md
   ```

2. **Provide Feedback**:
   ```bash
   # Document lessons learned, issues encountered, and suggestions
   nano .idse/projects/{project_name}/sessions/$(cat .idse/projects/{project_name}/CURRENT_SESSION)/feedback/feedback.md
   ```

### Session Status

Check pipeline progress:
```bash
idse status --project {project_name}
```

### Validation

Before syncing to Agency Core:
```bash
idse validate --project {project_name}
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

**Project Stack**: {stack}
**IDSE Version**: 0.1.0
**Generated**: {timestamp}
