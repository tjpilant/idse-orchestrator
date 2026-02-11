# Specification

## Overview
Audit and harden the existing DocToAgentProfileSpec compiler to close gaps identified in context.md. The compiler already exists with full pipeline (load → parse → merge → validate → emit). This session focuses on: SQLite-backed loading, end-to-end validation, schema documentation, and mapping rules.

## Functional Requirements

- FR-1: `SessionLoader` MUST read spec.md content from SQLite via `ArtifactDatabase.load_artifact()`, falling back to filesystem only when DB is unavailable.
- FR-2: `compile_agent_spec()` MUST accept a `backend` parameter to select SQLite or filesystem loading.
- FR-3: The compiler MUST produce a valid `AgentProfileSpec` YAML file at `.idse/projects/<project>/build/agents/<session>.profile.yaml`.
- FR-4: The compiler MUST validate all required fields (`id`, `name`) are present and non-empty.
- FR-5: The compiler MUST apply blueprint-to-feature inheritance: feature overrides blueprint where explicitly specified; blueprint provides defaults otherwise.
- FR-6: The `--dry-run` flag MUST print validated YAML to stdout without writing files.
- FR-7: The compiler MUST NOT call LLMs, external APIs, or import PromptBraining modules.

## Non-Functional Requirements
- Deterministic output: same inputs MUST produce byte-identical output (excluding timestamp comment)
- Schema version tracked in output: `version: "1.0"` field
- No new dependencies beyond what's in `pyproject.toml`

## Acceptance Criteria
- AC-1: `idse compile agent-spec --session agent-spec-compiler --project idse-orchestrator --dry-run` produces valid YAML from the `## Agent Profile` block in this spec.md
- AC-2: `SessionLoader` loads from SQLite when backend is sqlite
- AC-3: Compilation with missing required fields (`id`, `name`) raises `ValidationError`
- AC-4: Blueprint + feature merge produces expected override behavior
- AC-5: All existing compiler tests continue to pass (7 tests)
- AC-6: At least 3 new tests covering SQLite loading, end-to-end compilation, and validation errors

## Assumptions / Constraints / Dependencies
- Assumptions: `ArtifactDatabase` API is stable; `load_artifact()` returns content with `## Agent Profile` YAML block intact
- Constraints: No runtime dependencies; no PromptBraining imports
- Dependencies: `compiler/` package (existing), `ArtifactDatabase` (existing)

## AgentProfileSpec Schema

### Current Fields (Pydantic model in `compiler/models.py`)

| Field | Type | Required | Description |
|---|---|---|---|
| `id` | `str` | Yes | Stable identifier (e.g., `auth-service-agent`) |
| `name` | `str` | Yes | Human-readable name |
| `description` | `str` | No | Short summary of role and scope |
| `goals` | `List[str]` | No | Explicit goals for the agent |
| `inputs` | `List[str]` | No | Input types or schemas |
| `outputs` | `List[str]` | No | Output types or artifacts |
| `tools` | `List[str]` | No | Tool names the runtime may use |
| `constraints` | `List[str]` | No | Safety, cost, scope constraints |
| `memory_policy` | `Dict[str, Any]` | No | Named memory policies |
| `runtime_hints` | `Dict[str, Any]` | No | Non-required runtime preferences |
| `version` | `str` | No | Schema version (default `"1.0"`) |
| `source_session` | `str` | No | Provenance: originating session |
| `source_blueprint` | `str` | No | Provenance: blueprint session used |

### Mapping Rules (spec.md → AgentProfileSpec)

The `## Agent Profile` section in `spec.md` contains a fenced YAML block that maps directly to `AgentProfileSpec` fields. The parser (`compiler/parser.py`) extracts the first `yaml` code block under the `## Agent Profile` heading.

Inheritance: Blueprint `spec.md` Agent Profile provides defaults. Feature `spec.md` Agent Profile overrides. Deep merge for dicts; replacement for lists and scalars.

## Agent Profile

```yaml
id: agent-spec-compiler
name: AgentSpecCompiler Audit Session
description: Validates and hardens the DocToAgentProfileSpec compiler pipeline
goals:
  - Ensure SessionLoader reads from SQLite backend
  - Validate end-to-end compilation from spec.md to .profile.yaml
  - Document AgentProfileSpec schema and mapping rules
inputs:
  - spec.md with Agent Profile YAML block
  - Blueprint spec.md for inheritance defaults
outputs:
  - Validated .profile.yaml file
  - Schema documentation
tools:
  - Click CLI
  - Pydantic v2
  - PyYAML
constraints:
  - No LLM calls
  - No PromptBraining runtime imports
  - Deterministic output
memory_policy: {}
runtime_hints: {}
version: "1.0"
```
