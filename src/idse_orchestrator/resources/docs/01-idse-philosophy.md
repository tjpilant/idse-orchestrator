# IDSE Philosophy

**Intent-Driven Systems Engineering (IDSE)** is a unified methodology for AI-accelerated software development.

## Core Philosophy

> Software is the expression of intent, constrained by context, structured through specification, and realized through systematic engineering.

IDSE eliminates ambiguity by transforming:



Intent → Context → Specification → Plan → Tasks → Implementation → Feedback


Each phase outputs artifacts that guide the next.

## Goals

- Reduce ambiguity  
- Improve alignment between intent and implementation  
- Enable clean pivots  
- Codify reasoning, not just code  
- Create systems where specs **generate** code  

## Why intent, context, and specification are foundational

- **Intent** states the purpose and success criteria. It answers "What value are
  we delivering?" and anchors all downstream decisions.
- **Context** grounds choices in reality: scale, compliance, latency, teams,
  integrations, risks, and unknowns. It prevents designing for imagined
  conditions.
- **Specification** merges intent and context into a precise, testable contract.
  It captures functional and non-functional requirements, acceptance criteria,
  and open questions.

Intent sets direction, context sets boundaries, and specification defines the
agreement on what will be built. Code is not generated until the specification
is complete and a plan is in place; we revisit each pillar as new information
arrives.

## SDD principles adapted into IDSE

IDSE borrows and reframes key Specification-Driven Development concepts:

- **Executable specifications**: Structured Markdown specs feed implementation
  plans and tests so specs stay living and drive code.
- **Continuous refinement**: Feedback from testing and production flows back
  into intent, context, and specs instead of being patched in code alone.
- **Research-driven context**: Context work includes scale, compliance,
  personas, existing systems, and unknowns, informed by research rather than
  guesses.
- **Bidirectional feedback**: Issues update requirements and constraints; new
  goals update specs and plans.
- **Branching and exploration**: Alternative plans or tasks can be generated for
  experiments while preserving the original spec.
- **Constitutional guardrails**: Library-first, minimal abstraction, test-first,
  and integration-first practices from SDD are reflected in the IDSE
  constitution. Services must be observable (health checks, HTTP exercise) and
  avoid needless wrappers around framework features.

## Connecting philosophy to practice

- Start with an **intent** doc and refine until goals and success criteria are
  explicit; resist jumping to code or architecture.
- In **context** discovery, document scale, performance targets, compliance,
  dependencies, and unknowns; treat unanswered questions as blockers to resolve
  or track.
- The **specification** merges intent and context into user stories, functional
  and non-functional requirements, acceptance criteria, and open questions; it
  feeds plans and tests.

By sequencing intent → context → specification before planning and tasks, teams
maintain alignment, reduce scope creep, and keep implementation faithful to the
original intent.
