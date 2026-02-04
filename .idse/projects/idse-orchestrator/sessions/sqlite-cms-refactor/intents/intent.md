# Intent

## Goal
Refactor IDSE from file-first storage to a SQLite-based CMS so the database is the single source of truth while preserving on-demand file views for IDE agents.

## Problem / Opportunity
The current file-based pipeline makes state hard to query, increases sync complexity, and creates drift between local files and remote CMS backends. A SQLite core enables unified state, reliable sync, and predictable querying without abandoning IDE-friendly files.

## Stakeholders / Users
- Primary users and their goals:
  - IDSE maintainers: single source of truth, easier migrations, stable sync.
  - IDE agents (Claude/Codex/Copilot): keep markdown workflow via generated views.
  - Operators: reliable queries, consistent project/session metadata.

## Success Criteria (measurable)
- Baseline → Target: 0% of sessions stored in DB → 100% of new sessions stored in SQLite.
- Baseline → Target: manual sync + fragile parsing → deterministic SQL-backed sync with hash comparisons.
- All existing file-based projects can be migrated without data loss and without breaking legacy file backend.

## Constraints / Assumptions / Risks
- Business / Compliance:
  - Must remain backward compatible with file backend.
- Technical:
  - No new external dependencies (SQLite stdlib only).
- Known risks:
  - Migration gaps (files not mapped to DB fields).
  - Generated file views diverge from DB content if not refreshed.

## Scope
- In scope:
  - SQLite schema and DB manager.
  - DesignStoreSQLite backend.
  - Migration utilities (file → DB).
  - On-demand markdown file view generation.
  - CLI commands: export, migrate, query.
- Out of scope / non-goals:
  - Removing filesystem backend.
  - Remote CMS schema changes (Notion/Supabase).
  - Live sync automation without explicit CLI commands.
- Dependencies:
  - Existing DesignStore interface and sync pipeline.

## Time / Priority
- Deadline or target release: Next minor release after feature stabilization.
- Criticality / priority: High (foundation refactor for future sync).
