# Specification

## Overview
- Add file artifact support to DesignStore backends (filesystem + Notion MCP) with a
  shared metadata schema and deterministic lookup per session.

## User Stories
- As a developer, I want to attach files to a session so that artifacts live with the IDSE work.
- As a maintainer, I want deterministic identifiers so updates don’t create duplicates.

## Functional Requirements
- FR-1: DesignStore exposes file artifact CRUD (list/get/put/delete) and metadata.
- FR-2: Filesystem backend stores files under `.idse/projects/<project>/sessions/<session>/files/`.
- FR-3: Notion backend stores references or attachments in a consistent structure.
- FR-4: File artifacts are linked to a session and stage (if applicable).

## Non-Functional Requirements
- Performance (e.g., p95 latency, throughput)
- Scale (e.g., concurrent users, data volume)
- Compliance/security (e.g., residency, authz, logging)
- Reliability/resilience targets
- Best-effort sync; no silent overwrites without user confirmation.

## Acceptance Criteria
- AC-1: `idse sync push` includes file artifacts when enabled.
- AC-2: `idse sync pull` restores file artifacts to their expected locations.
- AC-3: File artifact metadata is queryable via DesignStore.

## Assumptions / Constraints / Dependencies
- Assumptions:
- Constraints:
- Notion MCP support for file upload may require link-only representation.
- Dependencies:
- Notion MCP schema capabilities for attachments.

## Open Questions
- What file size limits should be enforced per backend?
- Should file artifacts be versioned per session or overwritten?

## Agent Profile

```yaml
id: designstore-file-artifacts
name: DesignStore File Artifacts
description: Define DesignStore support for file/binary artifacts across backends.
goals:
  - Define file artifact metadata schema
  - Extend filesystem backend to store files
  - Design Notion backend strategy for attachments/links
inputs:
  - Current DesignStore interface
  - Notion MCP tool schemas
outputs:
  - Updated DesignStore API spec
  - Implementation plan for Notion backend
tools: []
constraints:
  - Preserve existing pipeline doc behavior
memory_policy:
  retention: session
runtime_hints:
  default_stage: spec
version: "1.0"
source_session: designstore-file-artifacts
source_blueprint: __blueprint__
```
