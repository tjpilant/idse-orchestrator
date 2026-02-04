# Specification

## Overview
Refactor IDSE orchestration to use SQLite as the authoritative store for projects, sessions, artifacts, and agents. Preserve IDE compatibility via on-demand markdown file views.

## User Stories
- As a maintainer, I want to query pipeline state via SQL so that status and sync are deterministic.
- As an IDE agent, I want to read markdown artifacts so that my workflow remains unchanged.
- As an operator, I want to migrate existing file projects without data loss.

## Functional Requirements
- FR-1: Persist projects, sessions, artifacts, and agent registry in SQLite at `.idse/idse.db`.
- FR-2: Provide a DesignStoreSQLite backend implementing DesignStore interface.
- FR-3: Generate markdown file views on-demand (export command and after init/session create).
- FR-4: Provide migration utilities to import existing file-based projects into SQLite.
- FR-5: Add CLI commands: `idse export`, `idse migrate`, `idse query`.
- FR-6: Maintain filesystem backend as a legacy option.

## Non-Functional Requirements
- Performance: CLI operations should remain fast for typical project sizes.
- Scale: Support multiple projects and sessions without schema changes.
- Compliance/security: No new external dependencies or services.
- Reliability: Migration is non-destructive and idempotent.

## Acceptance Criteria
- AC-1: `idse init` creates SQLite records and generates file views.
- AC-2: `idse export` regenerates markdown views matching DB content.
- AC-3: `idse migrate` imports an existing project and preserves all artifacts.
- AC-4: `idse status` and `idse query` read from SQLite when backend is sqlite.
- AC-5: Filesystem backend continues to work unchanged.

## Assumptions / Constraints / Dependencies
- Assumptions:
  - SQLite stdlib is available in target Python.
- Constraints:
  - No new external dependencies.
- Dependencies:
  - Existing DesignStore interface and current CLI structure.

## Open Questions
- How to handle custom artifact files outside the standard pipeline stages?
- Should migration include optional purge of file views after success?

## Agent Profile

```yaml
id: sqlite-cms-refactor
name: SQLite CMS Refactor
description: Implement SQLite-based CMS core with file view generation and migration.
goals:
  - Add SQLite schema and DB manager
  - Implement DesignStoreSQLite backend
  - Provide file view export and migration tools
inputs:
  - Existing IDSE project file structure
  - Plan: humble-twirling-cat.md
outputs:
  - SQLite-backed storage and CLI commands
  - On-demand markdown views
  - Migration utilities
constraints:
  - No new dependencies beyond stdlib
  - Preserve filesystem backend
memory_policy: {}
runtime_hints:
  mode: implementation
version: "1.0"
source_session: sqlite-cms-refactor
source_blueprint: __blueprint__
```
