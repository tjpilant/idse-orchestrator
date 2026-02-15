# Specification

## Intent

Define ZPromptCompiler v0.1 behavior for deterministic compilation of structured agent profiles into runtime-ready prompt artifacts.

## Context

This spec is used to test the `idse compile agent-spec` pipeline and ensure generated profile output remains schema-valid and stable for downstream consumers.

## Tasks

- Parse Agent Profile YAML from this specification.
- Validate against `AgentProfileSpec`.
- Emit compiled `.profile.yaml` output.

## Specification

### Functional Requirements

- FR-1: Compiler SHALL parse the `## Agent Profile` YAML block.
- FR-2: Compiler SHALL validate required fields (`id`, `name`).
- FR-3: Compiler SHALL emit deterministic YAML for downstream consumption.

### Acceptance Criteria

- AC-1: `idse compile agent-spec` succeeds for this session spec.
- AC-2: Output contains `id: zpromptcompiler-v0-1` and `name: ZPromptCompiler`.

## Agent Profile

```yaml
id: zpromptcompiler-v0-1
name: ZPromptCompiler
description: Compiles structured agent profile inputs into runtime-ready prompt artifacts.
goals:
  - Transform validated profile specifications into deterministic prompt outputs.
  - Preserve schema integrity and traceability across compilation stages.
inputs:
  - agent_profile_yaml
  - optional_blueprint_overrides
outputs:
  - compiled_prompt_bundle
  - compile_report
tools:
  - yaml
  - json
  - jinja2
constraints:
  - deterministic_output_only
  - no_hidden_inference
  - fail_fast_on_schema_violations
memory_policy:
  retain_days: 7
  scope: session
runtime_hints:
  timeout_seconds: 60
  retries: 1
version: "0.1"
source_session: agent-spec-compiler
source_blueprint: __blueprint__
```
