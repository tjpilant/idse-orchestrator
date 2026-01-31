# IDSE Prompting Guide

When asking Developer Agent for work, give clear context and name the stage you
want. Use these patterns to keep outputs consistent.

## What to include in your request
- Goal/intent and current stage
- Stack and constraints (scale, compliance, deadlines)
- Success metrics (measurable)
- Desired output format (e.g., `spec.md`, `plan.md`, `tasks.md`, code)

## Stage-specific prompts

### Intent
> “Act as Developer Agent. Capture intent for [feature/project]. Include goal,
> problem/opportunity, stakeholders, measurable success criteria, scope
> boundaries, constraints/risks, and priority. Use `kb/templates/intent-template.md`.”

### Context
> “Generate `context.md` using `kb/templates/context-template.md` for [feature].
> Capture stack, scale, integrations, constraints (compliance/security),
> deadlines, team capabilities, and risks/unknowns.”

### Specification
> “Based on this intent and context, create `spec.md` using
> `kb/templates/spec-template.md`: user stories, functional/non-functional
> requirements, acceptance criteria, assumptions/constraints/dependencies,
> open questions marked `[REQUIRES INPUT]`.”

### Plan
> “Create `plan.md` using `kb/templates/plan-template.md` and a test plan using
> `kb/templates/test-plan-template.md`. Cover architecture, components, data
> model, API contracts, test strategy, and phased delivery.”

### Tasks
> “Generate `tasks.md` using `kb/templates/tasks-template.md`, derived from the
> plan and contracts. Keep tasks atomic, note dependencies/owners, and mark
> parallelizable tasks with `[P]`.”

### Implementation
> “Implement tasks from `tasks.md`, test-first. Honor the plan and contracts.
> Note any deviations and update artifacts if needed.”

## Example request
```
Goal: Add real-time notifications
Stack: Next.js + Node API + Postgres + Redis
Stage: Specification
Output: spec.md using kb/templates/spec-template.md
Constraints: <2s delivery, GDPR, 5k concurrent users
```

## Do / Don’t
- Do: Provide intent + context before spec/plan; ask for clarifying questions.
- Do: Use `[REQUIRES INPUT]` for ambiguities until resolved.
- Don’t: Skip stages or ask for code without a plan/spec.
- Don’t: Leave acceptance criteria untestable.

## References
- Templates: `kb/templates/` (intent, context, spec, plan, tasks, test plan)
- Example: `kb/examples/real-time-notifications.md`
- Stage differences: `docs/04-idse-spec-plan-tasks.md`
- Agent handoffs: `docs/04-idse-agents.md`
- Constitution: `docs/02-idse-constitution.md`

## Stages

- Early stage → focus on Intent + Context + Specification  
- Spec ready → generate Plan  
- Plan ready → generate Tasks  
- Tasks ready → generate Implementation  
