# IDSE Pipeline



Intent → Context → Specification → Plan → Tasks → Implementation → Feedback


## Intent
Define goals, outcomes, success metrics.

## Context
Document environment, constraints, scale, compliance, risks.

## Specification
Structured system requirements:
- User stories
- Functional requirements
- Acceptance criteria
- Non-functional requirements

## Plan
Architecture, components, models, APIs, strategy.
- Documented architecture diagrams and design decisions
- Component descriptions and relationships
- API contracts and data models (documented, not implemented)
- Implementation strategy and approach

## Tasks
Atomic units with clear testability and safe parallelization.

## Implementation
**For IDSE Agency:** Documentation artifacts that guide code creation:
- Validation reports confirming tasks were executed
- Code snippet examples (illustrative, in markdown)
- References to actual code locations in the codebase
- Handoff records to IDE/development team
- **NOT** production code, working schemas, or executable artifacts

**For IDE/Development Team:** Actual executable code lives in the codebase:
- Source code in appropriate directories (src/, backend/, frontend/, etc.)
- Tests, configs, and production artifacts
- These are created by reading the IDSE pipeline documents

## Feedback
Production learnings that update specs.
