# Context

## 1. Environment

- **Product / Project:** IDSE Orchestrator — design-time Documentation OS
- **Domain:** Developer tooling, agent-driven development pipelines
- **Users / Actors:**
  - IDSE developers authoring pipeline docs with `## Agent Profile` YAML blocks
  - CI pipelines running `idse compile agent-spec` as a build step
  - PromptBraining runtime (downstream consumer — reads `.profile.yaml`, never imports IDSE)

## 2. Stack

- **Language:** Python 3.8+
- **CLI:** Click 8.x
- **Validation:** Pydantic v2 (`AgentProfileSpec` model)
- **Serialization:** PyYAML for YAML parsing and emission
- **Storage:** SQLite via `ArtifactDatabase` (source of truth), filesystem `.md` as generated views
- **Templates:** Jinja2 for scaffold generation (spec-template.md includes `## Agent Profile` block)

## 3. Existing Implementation

The compiler was built during initial repo extraction (commit `fa9a3d3`, 2026-02-02).

| Module | Path | Role |
|---|---|---|
| `__init__.py` | `compiler/__init__.py` | Orchestrates: load → parse → merge → emit |
| `models.py` | `compiler/models.py` | `AgentProfileSpec` Pydantic model |
| `parser.py` | `compiler/parser.py` | Extracts `## Agent Profile` YAML block from spec.md |
| `loader.py` | `compiler/loader.py` | `SessionLoader` — reads spec.md from filesystem |
| `merger.py` | `compiler/merger.py` | Deep-merges blueprint defaults with feature overrides |
| `emitter.py` | `compiler/emitter.py` | Validates via Pydantic, writes `{session}.profile.yaml` |
| `errors.py` | `compiler/errors.py` | `AgentProfileNotFound`, `InvalidAgentProfileYAML`, `ValidationError` |

CLI: `idse compile agent-spec --session <id> --project <name> --blueprint <id> --out <dir> --dry-run`

Tests: 7 passing across `tests/test_compiler/` (models, parser, emitter, merger).

## 4. Constraints

- **No LLM calls** — compiler is deterministic, design-time only (blueprint invariant)
- **No PromptBraining imports** — output is a file, not a function call
- **SQLite is source of truth** — `SessionLoader` currently reads filesystem directly, bypassing the DB. This is a known gap.
- **Schema versioning** — `AgentProfileSpec.version` field exists but no migration strategy for schema evolution

## 5. Gaps Identified

| Gap | Impact | Severity |
|---|---|---|
| `SessionLoader` reads filesystem, not SQLite | Inconsistent with "SQLite is source of truth" invariant | High |
| No end-to-end test with real project data | Exit criteria unvalidated | Medium |
| `AgentProfileSpec` schema not published/shared | PromptBraining can't validate on read | Medium |
| No `doc2spec-mapping.md` documentation | Mapping rules implicit in parser code | Low |
| No versioning strategy for schema evolution | Risk of silent breakage | Low |

## 6. Risks & Unknowns

- **Schema drift:** If PromptBraining evolves its expectations independently, compiled specs may become invalid. Mitigation: version field + shared schema definition.
- **YAML-only input:** Parser only reads `## Agent Profile` YAML blocks. If future sessions need richer compilation (e.g., from intent.md goals, plan.md constraints), the parser will need extension.
- **Blueprint inheritance edge cases:** `merger.py` does deep dict merge with list/scalar replacement. Edge cases with nested tool configs or memory policies untested.
