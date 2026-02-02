# Intent: IDSE Developer Orchestrator

## Objective

Build a standalone, pip-installable CLI tool that manages Intent-Driven Systems Engineering (IDSE) projects in client workspaces. The orchestrator coordinates IDE agents (Claude Code, GPT Codex) and manages pipeline artifacts locally with a CMS-agnostic storage abstraction.

## Success Criteria

- Installable via `pip install idse-orchestrator`
- CLI commands: init, validate, status, session create/switch, spawn, compile agent-spec, sessions, session-info, docs install, generate-agent-files
- 7-stage pipeline: intent → context → spec → plan → tasks → implementation → feedback
- Constitutional validation via governance rules
- Agent routing via registry
- DesignStore abstraction for future CMS backends (Notion, Supabase, Firebase)
- Self-dogfooding: this repo uses its own `.idse/` structure

## Stakeholders

- IDSE Developer Agency (maintainer)
- Client workspace developers (users)
- IDE agents: Claude Code, GPT Codex (consumers of agent instructions and routing)

## Constraints

- Python >=3.8
- No runtime LLM calls — deterministic operations only
- Per-workspace, per-repo (no global state)
- CLI-first, CI-friendly
