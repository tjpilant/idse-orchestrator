# AI Agent Instructions for {project_name}

## For: Claude Code, GitHub Copilot, Cursor, GPT Codex, and other AI assistants

This project uses **IDSE (Intent-Driven Systems Engineering)**.

### Quick Start

1. **Find the current session**:
   ```
   cat .idse/projects/{project_name}/CURRENT_SESSION
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
.idse/projects/{project_name}/
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
idse status --project {project_name}

# Validate before syncing
idse validate --project {project_name}

# Sync to Agency Core
idse sync push --project {project_name}
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

**Project**: {project_name}
**Stack**: {stack}
**IDSE Version**: 0.1.0
