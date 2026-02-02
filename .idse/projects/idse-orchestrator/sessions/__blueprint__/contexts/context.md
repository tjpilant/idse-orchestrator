# Context: IDSE Developer Orchestrator

## Background

The IDSE Orchestrator was extracted from the idse-developer-agency monorepo to become a standalone product. It implements the Documentation OS pattern where design-time cognition is separated from run-time cognition.

## Technical Context

- **Language**: Python 3.8+
- **Framework**: Click (CLI), Pydantic v2 (models), Jinja2 (templates), PyYAML
- **Architecture**: 18 modules organized by Product Spine primitives
- **Storage**: Filesystem-based with DesignStore abstraction for future backends
- **Testing**: pytest with 13+ tests

## Key Modules

| Module | Spine Primitive |
|--------|----------------|
| project_workspace.py | ProjectWorkspace |
| session_graph.py | SessionGraph |
| pipeline_artifacts.py | PipelineArtifacts |
| stage_state_model.py | StageStateModel |
| validation_engine.py | ValidationEngine |
| constitution_rules.py | ConstitutionRules |
| design_store.py | DesignStore + DesignStoreFilesystem |
| agent_registry.py | AgentRegistry |
| ide_agent_routing.py | IDEAgentRouting |
| compiler/ | DocToAgentProfileSpecCompiler |
| cli.py | CLIInterface |

## Dependencies

- click>=8.1.0, pydantic>=2.0.0, jinja2>=3.1.0, pyyaml>=6.0.0
- Dev: pytest, pytest-cov, black, flake8, mypy

## Related Systems

- IDSE Constitution (Articles I-X) — governance framework
- Agency Swarm — multi-agent orchestration framework
- PromptBraining — future integration for agent profile compilation
