# Getting Started with the IDSE Developer Agent

Welcome to the **IDSE Developer Agent** project. This guide helps AI agents and
human contributors get productive quickly. It explains how to use the
repository, follow the IDSE methodology, and contribute effectively.

## 1. Repository Overview

This repo defines the Intent-Driven Systems Engineering (IDSE) methodology and
includes:

- `docs/` – Philosophy, pipeline, constitution, prompting, patterns, and this
  guide.
- `kb/templates/` – Templates for intent, context, specs, plans, tasks, and test
  plans.
- `kb/examples/` – End-to-end examples of the IDSE pipeline.
- `kb/playbooks/` – Operational playbooks for features, refactors, bug fixes,
  and change requests.
- `prompts/` – System prompts to configure a Custom GPT as a Developer Agent.
- `AGENTS.md` – Guidelines for AI assistants and human contributors.
- `.github/workflows/validate-kb.yml` – CI check that fails if unresolved
  REQUIRES INPUT markers remain in docs or examples.

## 2. Using the Developer Agent

The Developer Agent acts as a virtual senior engineer who follows the IDSE
pipeline:

1. **Clarify intent and context:** Create `intent.md` and `context.md` from
   `kb/templates/`, capturing goals, success criteria, stack, constraints, and
   risks.
2. **Generate a specification:** Draft `spec.md` with functional and
   non-functional requirements, user stories, and acceptance criteria. Mark
   unknowns with a REQUIRES INPUT marker until resolved.
3. **Produce an implementation plan:** Write `plan.md` with architecture,
   components, data models, API contracts, test strategy, and phases.
4. **Break down into tasks:** Write `tasks.md` with atomic tasks derived from
   the plan. Mark independent work with `[P]`.
5. **Implement:** Generate code and tests to satisfy tasks, honoring the plan
   and specification.
6. **Validate:** Ensure all REQUIRES INPUT markers are cleared; run tests per
   the plan.
7. **Review and iterate:** Apply feedback from reviews and production; update
   intent, context, or specs as needed.

## 3. Creating a New Project Session

**Authority:** Article X of the IDSE Constitution

All IDSE project sessions must be created using the official SessionManager to ensure proper folder scaffolding, canonical artifact locations, and audit trail compliance.

### Quick Start

Use the CLI to create a new project session:

```bash
idse init <ProjectName> --stack <stack>
```

**Example:**
```bash
idse init IDSE_Core --stack python
```

### What Gets Created

The SessionManager creates:

1. **Canonical Projects-Root Directories** (Article X, Section 3):
   ```
   projects/<ProjectName>/sessions/<session-name>/intents/
   projects/<ProjectName>/sessions/<session-name>/contexts/
   projects/<ProjectName>/sessions/<session-name>/specs/
   projects/<ProjectName>/sessions/<session-name>/plans/
   projects/<ProjectName>/sessions/<session-name>/tasks/
   projects/<ProjectName>/sessions/<session-name>/implementation/
   projects/<ProjectName>/sessions/<session-name>/feedback/
   ```

2. **Project Visibility Folder**:
   - `projects/<ProjectName>/README.md` – Project overview
   - `projects/<ProjectName>/CURRENT_SESSION` – Authoritative pointer to active session (Article X, Section 4)

3. **Session Metadata**:
   - `.idse_active_session.json` – Updated with new session
   - `.idse_sessions_history.json` – Session appended to history
   - `projects/<ProjectName>/sessions/<session-name>/specs/.owner` – Ownership marker

4. **Audit Trail** (Article X, Section 7):
   - `projects/<ProjectName>/sessions/<session-name>/feedback/bootstrap_<ProjectName>_<timestamp>.md`

### Validation

After bootstrapping, validate the session structure:

```bash
idse validate --project <ProjectName>
```

### Important Notes

- **Canonical Paths:** Use projects-rooted paths (`projects/<Project>/sessions/<session>/<stage>/...`) as the source of truth
- **Active Session Pointer:** The `projects/<ProjectName>/CURRENT_SESSION` file is authoritative for resolving the active session
- **Legacy Stage-Root:** Stage-rooted paths are legacy and only valid during the grace period; migrate with the provided tooling
- **Manual Creation Prohibited:** Article X, Section 5 forbids manual session directory creation—always use SessionManager
- **Human-Readable Session Names:** Use descriptive names like `puck-components`, not timestamps
- **Session Metadata:** Store owner/collaborators/changelog/project README/checklist under `projects/<Project>/sessions/<session>/metadata/` (see `docs/09-metadata-sop.md`)

### Legacy Stage-Root Grace Policy (Article X Section 6) and Metadata (Section 8)

The canonical root is now `projects/<Project>/sessions/<session>/<stage>/...`. Use this checklist to manage legacy stage-rooted paths during the grace period:

- **Validators:** Use `idse validate`, which defaults to projects-rooted paths. Treat stage-rooted paths as legacy only.
- **SessionManager:** Scaffolds projects-rooted paths and emits legacy notices into stage-rooted locations without overwriting existing files.
- **Data migration:** Use a migration script to move artifacts from `<stage>/projects/.../sessions/...` into `projects/<project>/sessions/<session>/<stage>/`, with dry-run, logs under `projects/<project>/sessions/<session>/feedback/`, and rollback plan.
- **CI enforcement:** Add a CI job to fail new writes to stage-rooted paths after the grace window; optional pre-commit warning.
- **Docs/update:** Stage-rooted paths are legacy; `projects/<Project>/CURRENT_SESSION` is authoritative.

Migration task list:
- Phase A (dual-mode ready): Validators + SessionManager prefer new layout, keep legacy reads limited and explicit.
- Phase B (canary): Migrate 1–2 projects with the script; fix drift; run validators in both modes.
- Phase C (full migration): Migrate remaining projects; enable CI enforcement; remove temporary pointers.
- Phase D (cleanup): Remove transitional flags; treat stage-rooted writes as failures; update any tooling/scripts that still assume stage-rooted paths.

Session metadata (Article X Section 8):
- Store owner/collaborators/changelog/project README/checklist under `projects/<Project>/sessions/<session>/metadata/`.
- Use `projects/<Project>/CURRENT_SESSION` to resolve the active session before writing metadata.
- Project-root metadata files are read-only; do not write there after grace.

### Next Steps After Bootstrap

1. Start with the Intent stage: Create `projects/<ProjectName>/sessions/<session-name>/intents/intent.md`
2. Follow the IDSE pipeline: Intent → Context → Spec → Plan → Tasks → Implementation → Feedback
3. Use templates from `kb/templates/` as starting points
4. Keep all artifacts in their canonical locations

## 4. Running the Validation Workflow

Run the CI check locally to ensure no unresolved placeholders remain:

```bash
grep -R "REQUIRES INPUT" -n kb/ docs/ --exclude-dir templates \
  || echo "✔ No unresolved inputs"
```

Templates under `kb/templates/` intentionally contain placeholders and are
excluded from the check.

## 5. Contributing Guidelines

- Describe changes: Note which artifacts (intent, context, spec, plan, tasks,
  docs) you updated and why.
- Follow IDSE principles: Respect the constitution (intent supremacy, context
  alignment, specification completeness, test-first, simplicity, transparency,
  plan-before-build, atomic tasking, feedback incorporation).
- Commit messages: Be clear and refer to the artifact or stage (e.g., "Add test
  plan template", "Refine notification plan for GDPR logging").
- Do not commit secrets: Never include keys or tokens.
- Multiple packages: If you add subprojects, include an `AGENTS.md` in each with
  package-specific guidance.

## 6. Learning More

- **Philosophy:** `docs/01-idse-philosophy.md`
- **Constitution:** `docs/02-idse-constitution.md` (includes Article X on Project Bootstrap)
- **Artifacts compared:** `docs/04-idse-spec-plan-tasks.md`
- **SDD to IDSE evolution:** `docs/07-sdd-to-idse.md`
- **Example walkthrough:** `kb/examples/real-time-notifications.md`

IDSE is a living methodology—suggest improvements, add templates or playbooks,
and keep artifacts consistent so teams and agents build better systems together.
