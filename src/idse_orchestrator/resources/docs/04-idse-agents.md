# IDSE Agent Framework

IDSE uses a multi-agent conceptual model:

## Intent Agent
- **Inputs:** User prompt/ask.
- **Outputs:** `intent.md` using `kb/templates/intent-template.md`.
- **Scope:** Purpose, problem/opportunity, stakeholders/users, measurable
  success criteria, scope boundaries, constraints/risks, priority/timing.
- **Handoffs:** Must have explicit success metrics and no missing sections
  before Context Agent proceeds.

## Context Agent
- **Inputs:** Approved intent; follow-up answers.
- **Outputs:** `context.md` using `kb/templates/context-template.md`.
- **Scope:** Scale, stack, integrations, constraints, compliance, team
  capabilities, deadlines, risks/unknowns.
- **Handoffs:** Documented constraints and risks; unanswered items marked and
  resolved before Spec Agent proceeds.

## Specification Agent
- **Inputs:** Intent + context.
- **Outputs:** `spec.md` using `kb/templates/spec-template.md`.
- **Scope:** User stories, functional and non-functional requirements,
  acceptance criteria, assumptions/constraints/dependencies, open questions.
- **Handoffs:** No `[REQUIRES INPUT]` markers; all acceptance criteria testable
  and traceable before Plan Agent proceeds.

## Plan Agent
- **Inputs:** Approved spec.
- **Outputs:** `plan.md` using `kb/templates/plan-template.md` and a test plan
  using `kb/templates/test-plan-template.md`.
- **Scope:** Architecture summary, components, data models, API contracts, test
  strategy, phases.
- **Handoffs:** Test plan defined; components and contracts cover all spec
  requirements before Task Agent proceeds.

## Task Agent
- **Inputs:** Plan + test plan.
- **Outputs:** `tasks.md` using `kb/templates/tasks-template.md`.
- **Scope:** Atomic, testable tasks organized by phase; dependencies noted;
  parallelizable tasks marked `[P]`.
- **Handoffs:** Tasks trace to plan components/contracts; dependencies and
  acceptance notes clear before Implementation Agent proceeds.

## Implementation Agent
- **Inputs:** Tasks, plan, contracts, test plan.
- **Outputs:** Code, tests, migrations/configs to satisfy tasks; notes on any
  deviations from spec/plan.
- **Scope:** Test-first implementation; respects architecture/contracts; keeps
  simplicity and transparency.
- **Handoffs:** Reports coverage against tasks/spec; updates artifacts if
  deviations occur.

All Agents follow the IDSE Constitution (intent supremacy, context alignment,
spec completeness, test-first, simplicity, transparency, plan-before-build,
atomic tasking, feedback incorporation).
