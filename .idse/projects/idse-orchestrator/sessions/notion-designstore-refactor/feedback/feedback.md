# Feedback

## External / Internal Feedback
- 2026-02-07: Requested mission-report style blueprint rollup capturing both deliverables and lessons learned.
- 2026-02-07: Requested stronger extraction to avoid placeholder noise and overlong bullets in high-level meta view.
- 2026-02-07: Requested explicit split where SQLite is core storage and Notion/filesystem are sync targets only.

## Impacted Artifacts
- Intent: No changes
- Context: No changes
- Spec: No changes
- Plan / Test Plan: No changes
- Tasks / Implementation: Updated implementation notes with completed metadata-rollup work

## Risks / Issues Raised
- Placeholder-heavy feedback artifacts can pollute rollups if not filtered.
- Narrow section matching misses summaries when teams vary heading style.
- Single `artifact_backend` setting caused status/validation drift by switching storage behavior unintentionally.

## Actions / Follow-ups
- Populate `notion-designstore-refactor` implementation and feedback artifacts with real content so it appears in blueprint summaries.
- Migrate configs to `storage_backend` + `sync_backend`; keep `artifact_backend` as legacy compatibility only.

## Decision Log
- Added `Feedback & Lessons Learned` rollup to blueprint meta.
- Enforced section variants (`Summary`, `Executive Summary`, `Lessons Learned`) and bullet truncation (200 chars).
- Storage/sync split adopted:
  - Storage default remains SQLite (`storage_backend`).
  - Sync target uses independent `sync_backend`.
  - Legacy `artifact_backend=notion` no longer overrides storage backend.
