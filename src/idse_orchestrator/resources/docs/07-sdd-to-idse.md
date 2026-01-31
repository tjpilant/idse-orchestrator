# From SDD to IDSE: Evolution of a Methodology

Intent-Driven Systems Engineering (IDSE) evolved from earlier work on
Specification-Driven Development (SDD). SDD introduced powerful ideas, and the
shift to IDSE reflects lessons learned and a change in emphasis. This summary
explains how they connect.

## Background: Specification-Driven Development

SDD centered on executable specifications driving the entire lifecycle. It
introduced commands like `/speckit.specify`, `/speckit.plan`, and
`/speckit.tasks` to generate specs, plans, and tasks. Core ideas included:

- **Specifications as lingua franca:** Everything starts from an executable
  spec.
- **Executable documents:** Specifications can be run to validate correctness
  and compliance.
- **Continuous refinement:** Specs evolve through feedback loops.
- **Library-first development:** Favor libraries over frameworks when possible.
- **CLI-required:** Expose functionality via command line for observability and
  testing.
- **Test-first mandate:** Write tests before implementation.

## Motivation for IDSE

SDD could feel prescriptive for teams with diverse constraints. Practitioners
found intent and context often needed to lead. IDSE retains structure and
testing but starts from the goals and environment.

## What Changed

- **From specification to intent:** IDSE begins by clarifying outcomes before
  diving into specs.
- **Context as first-class:** Constraints, environment, and risks shape the spec
  and plan.
- **Tool flexibility:** Rather than enforcing `/speckit.*`, IDSE emphasizes
  principles over specific CLI workflows.
- **Unified constitution:** SDD articles are reframed under IDSE guardrails
  (intent supremacy, context alignment, specification completeness, test-first,
  simplicity, transparency, plan-before-build, atomic tasking, feedback
  incorporation).
- **Modern tools:** Designed to pair with AI developer tools and knowledge bases
  instead of a single library.

## Continuities

- **Structured artifacts:** Specs, plans, and tasks remain the backbone.
- **Test-first mindset:** Tests come before code.
- **Feedback loops:** Production and testing feedback refine artifacts.
- **Library and CLI values:** Emphasis on simplicity, observability, and clear
  interfaces persists.

## Why It Matters

The SDD-to-IDSE evolution shows that dropping "speckit" was not about losing
structure. It elevated intent and context while keeping executable specs and
test-first discipline. Knowing the lineage helps contributors reuse proven
patterns and avoid reinventing process.
