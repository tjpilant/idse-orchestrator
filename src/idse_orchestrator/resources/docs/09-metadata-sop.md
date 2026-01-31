# SOP: Session Metadata (Owner, Collaborators, Changelog, Checklist, Project README)

## Purpose
Define the canonical locations and update rules for session-level metadata files (owner, collaborators, changelog, project README pointer, review checklist) in the projects-root layout.

## Scope
- Applies to all projects/sessions using the projects-root canonical mapping (`projects/<project>/sessions/<session>/...`).
- Covers: `.owner`, `.collaborators`, `changelog.md`, `project-readme.md`, `review-checklist.md`.

## Canonical Locations
- Base: `projects/<project>/sessions/<session>/metadata/`
- Required files:
  - `.owner` — session owner
  - `.collaborators` — collaborators list
  - `changelog.md` — running changelog for the session
  - `project-readme.md` — session-aware project README (status/overview)
  - `review-checklist.md` — checklist for reviews/gates
- Optional: other session-scoped docs (risk log, decisions, ADR links).

## Rules
- **Write here, not project root:** All pipeline-driven updates to changelog/README/checklists must target the session metadata directory, not `projects/<project>/...` root files.
- **CURRENT_SESSION pointer is authoritative:** Resolve the active session via `projects/<project>/CURRENT_SESSION`, then write metadata under that session’s `metadata/` folder.
- **No stage-root writes:** Legacy stage-root paths are deprecated; do not write metadata there.
- **Auditability:** Metadata changes are part of the session history; include meaningful entries in `changelog.md` when making changes.

## Migration Guidance
- If project-root metadata files exist (e.g., `projects/<project>/changelog.md`), copy their content into `projects/<project>/sessions/<session>/metadata/` for the active session. Keep the project-root copy read-only or remove it after validation.
- Legacy stage-root locations must not be used for metadata.

## Pipeline Usage
- During each stage update (Intent/Context/Spec/Plan/Tasks/Implementation/Feedback), update the session changelog and, if relevant, the review checklist under `metadata/`.
- Implementation README can reference `metadata/` for collaborators/owner/changelog/checklist pointers.

## Enforcement (recommended)
- Validator enhancement: warn/fail if metadata files are missing under `metadata/` for the active session, or if writes occur to project-root equivalents.
- CI/pre-commit guard: block new writes to project-root metadata files (except pointers) and stage-root locations.
