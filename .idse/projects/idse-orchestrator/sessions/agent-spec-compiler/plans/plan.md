# Plan — agent-spec-compiler

## 0. Product Overview

**Goal / Outcome:**
Harden the existing DocToAgentProfileSpec compiler so it aligns with the "SQLite is source of truth" invariant, passes end-to-end validation, and is documented well enough for PromptBraining to consume its output.

**Problem Statement:**
The compiler was built during initial extraction (Feb 2026) and works against filesystem reads. It has never been exercised against a real project or validated against the blueprint's exit criteria. The `SessionLoader` bypasses SQLite, violating the project's core invariant.

**Target Users:**
- IDSE developers running `idse compile agent-spec` to produce `.profile.yaml`
- CI pipelines automating spec compilation
- PromptBraining (downstream consumer of compiled specs)

**Success Metrics:**
- All acceptance criteria from spec.md pass
- 10+ compiler tests passing (7 existing + 3 new minimum)
- End-to-end: this session's own `spec.md` compiles to a valid `.profile.yaml`

## 1. Architecture Summary

```
spec.md (## Agent Profile YAML block)
    │
    ▼
SessionLoader ──── reads from SQLite (primary) or filesystem (fallback)
    │
    ▼
parse_agent_profile() ──── extracts YAML block under ## Agent Profile
    │
    ▼
merge_profiles() ──── deep-merges blueprint defaults + feature overrides
    │
    ▼
AgentProfileSpec ──── Pydantic validation
    │
    ▼
emit_profile() ──── writes {session}.profile.yaml to build/agents/
```

No changes to this architecture. The work is:
1. Make `SessionLoader` read from SQLite
2. Add tests for the full chain
3. Document the schema and mapping

## 2. Components

| Component | Responsibility | Parent Primitive |
|---|---|---|
| `SessionLoader` | Load spec.md from SQLite or filesystem | `DocToAgentProfileSpecCompiler` |
| `parse_agent_profile` | Extract YAML from `## Agent Profile` heading | `DocToAgentProfileSpecCompiler` |
| `merge_profiles` | Deep-merge blueprint + feature profiles | `DocToAgentProfileSpecCompiler` |
| `AgentProfileSpec` | Pydantic model for validation | `DocToAgentProfileSpecCompiler` |
| `emit_profile` | Write validated YAML to disk | `DocToAgentProfileSpecCompiler` |
| CLI `compile agent-spec` | User-facing command | `CLIInterface` |

## 3. Data Model

`AgentProfileSpec` (Pydantic model — no DB table, output-only):
- `id: str` (required)
- `name: str` (required)
- `description: Optional[str]`
- `goals: List[str]`
- `inputs: List[str]`
- `outputs: List[str]`
- `tools: List[str]`
- `constraints: List[str]`
- `memory_policy: Optional[Dict[str, Any]]`
- `runtime_hints: Optional[Dict[str, Any]]`
- `version: str` (default "1.0")
- `source_session: Optional[str]`
- `source_blueprint: Optional[str]`

## 4. API Contracts

CLI interface (already wired):
```
idse compile agent-spec \
  --session <session_id>       # required
  --project <project_name>     # optional, auto-detect
  --blueprint <blueprint_id>   # optional, default __blueprint__
  --out <output_dir>           # optional, default build/agents/
  --dry-run                    # optional, print YAML to stdout
```

## 5. Test Strategy

- **Existing tests (7):** model validation, parser extraction, emitter output, merger behavior
- **New tests (Phase 2):**
  - SQLite-backed `SessionLoader` reads artifact content correctly
  - End-to-end: `compile_agent_spec()` with filled spec.md produces valid YAML
  - Validation error on missing required fields (`id`, `name`)
  - Blueprint + feature merge override behavior
- **Tool:** pytest

## 6. Phases

### Phase 0 — Audit existing compiler
- Read all 7 modules in `compiler/`
- Run existing tests, confirm 7 pass
- Identify any code-level issues beyond the known gaps

### Phase 1 — SQLite-backed SessionLoader
- Update `SessionLoader` to accept a backend parameter
- When `backend="sqlite"`, load via `ArtifactDatabase.load_artifact(project, session_id, "spec").content`
- Fall back to filesystem when DB is unavailable or backend is explicitly `"filesystem"`
- Update `compile_agent_spec()` to pass backend through

### Phase 2 — Tests and validation
- Add test for SQLite loading path
- Add end-to-end test: create a temp project with filled `## Agent Profile` YAML, compile, validate output
- Add test for missing required fields
- Add test for blueprint + feature merge
- Confirm all tests pass (7 existing + new)

### Phase 3 — Documentation and self-test
- Run `idse compile agent-spec --session agent-spec-compiler --project idse-orchestrator --dry-run` to self-validate
- Write implementation/README.md and feedback/feedback.md
- Sync to DB
