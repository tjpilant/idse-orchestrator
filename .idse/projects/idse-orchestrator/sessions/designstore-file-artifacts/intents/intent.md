# Intent

## Goal
Enable DesignStore backends (filesystem and Notion MCP) to handle non-markdown file artifacts
in a consistent, session-scoped way without polluting the constitutional pipeline docs.

## Problem / Opportunity
Current sync only handles pipeline markdown. Teams need to store binary or auxiliary files
(design assets, datasets, images, zipped specs) alongside sessions without ad-hoc hacks.

## Stakeholders / Users
- Primary users and their goals:
  - IDSE maintainers: keep pipeline clean while supporting file artifacts.
  - Developers/Designers: attach files to sessions and retrieve them reliably.
  - IDE agents: read file references without direct MCP access.

## Success Criteria (measurable)
- Baseline → Target:
- Baseline → Target:
  - 0 → 1 stable interface for file artifact CRUD across DesignStore backends.
  - 0% → 100% of file artifacts tracked in session metadata with deterministic paths/IDs.

## Constraints / Assumptions / Risks
- Business / Compliance:
  - Do not store secrets in file artifacts by default.
- Technical:
  - Keep DesignStore interface backward compatible.
  - Do not require MCP access for agents.
- Known risks:
  - Backend-specific limits (Notion size caps, file type handling).
  - Duplication or orphaned files without cleanup policy.

## Scope
- In scope:
  - File artifact registry (metadata), upload/download/delete hooks in DesignStore.
  - Filesystem backend implementation.
  - Notion backend strategy (links or storage via Notion file blocks).
- Out of scope / non-goals:
  - Full asset management system.
  - Agent-side direct MCP access to files.
- Dependencies:
  - DesignStore interface changes.
  - Notion MCP file/attachment support (if available).

## Time / Priority
- Deadline or target release:
  - Target: next iteration after Notion MCP sync stabilization.
- Criticality / priority:
  - Medium-high (blocks real client usage with assets).
