# Specification vs. Plan vs. Tasks

Understanding the distinctions among specifications, implementation plans, and
task lists prevents confusion and keeps work traceable. In IDSE, each artifact
serves a distinct purpose and is produced in its own stage.

## Specifications (Spec)

A specification captures *what* the system should do and *why*. It defines
functional and non-functional requirements, user stories, and acceptance
criteria. Specs are written after intent and context are clear and act as the
source of truth for desired behavior.

### Characteristics

- Focus on user and system behavior rather than technical implementation.
- Define acceptance criteria and open questions.
- Are reviewable by stakeholders, PMs, and designers.
- Stay stable but evolve through feedback loops.

### Example (excerpt)

> **Functional Requirement:** Deliver a notification to the user within 2
> seconds of a related event occurring.
>
> **Acceptance Criterion:** Given a user places an order, when the order status
> changes to "shipped," then the user receives a notification badge update
> within 2 seconds.

## Implementation Plans (Plan)

An implementation plan describes *how* the specification will be realized. It
provides high-level architecture, components, data models, API contracts, and
test strategy. Plans break the spec into logical phases and ensure alignment
with context and constraints.

### Characteristics

- Map specification requirements to system components.
- Identify dependencies and interactions.
- Define data schemas and API contracts.
- Outline sequence of work (phases).
- Serve as reference for developers and reviewers.

### Example (excerpt)

> **Component:** Notification Service – exposes REST endpoints to fetch and
> acknowledge notifications; publishes events to Redis; writes to PostgreSQL.
>
> **Data Model:** `notifications` table with fields `id`, `user_id`, `type`,
> `message`, `created_at`, `read_at` and an index on `(user_id, read_at)`.

## Task Lists (Tasks)

A task list breaks the implementation plan into atomic units of work. Tasks are
assignable, testable, and often parallelizable. They ensure development moves
in small increments and each piece can be tracked and validated.

### Characteristics

- Derived directly from the implementation plan.
- Each task has a clear objective and deliverable.
- Small enough to complete in a day or a sprint.
- Marked as parallelizable (`[P]`) if independent.
- Provide traceability back to the spec via the plan.

### Example (excerpt)

> **Task 0.1:** Create DB migration for `notifications` table.
>
> **Task 1.3:** Build React notification panel with badge and slide-in panel.

## Summary

- **Specification:** Defines *what* and *why*; audience includes product, design
  and engineering; covers user stories, functional and non-functional
  requirements, acceptance criteria, and open questions.
- **Implementation plan:** Describes *how* to implement; audience is architects,
  engineers, and reviewers; covers architecture, components, data models, API
  contracts, test strategy, and phases.
- **Task list:** Outlines *work to be done*; audience is developers and project
  managers; covers detailed tasks, dependencies, and parallelization markers.

Each artifact informs the next stage and together they provide a complete,
traceable picture from intent to implementation.
