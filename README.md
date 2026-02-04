# IDSE Developer Orchestrator

A pip-installable CLI tool for managing Intent-Driven Systems Engineering (IDSE) projects in client workspaces.

## Overview

The IDSE Orchestrator is a standalone per-workspace tool:

IDSE Orchestrator (This package - per workspace) ↕ Coordinates IDE Agents (Claude Code, GPT Codex)

## Features

- **Project Initialization**: Generate complete IDSE pipeline structure with templates
- **Validation**: Check artifacts for constitutional compliance
- **State Tracking**: Monitor pipeline stage progression
- **Agent Coordination**: Route tasks to appropriate IDE agents (Claude ↔ Codex)

## Installation

### From Source (Development)

```bash
cd idse-orchestrator
pip install -e .
```

### From PyPI (Future)

```bash
pip install idse-orchestrator
```

## Quick Start

### 1. Initialize a New Project

```bash
idse init customer-portal --stack python
```

This creates:

```
.idse/
└── projects/
    └── customer-portal/
        ├── sessions/
        │   └── session-<timestamp>/
        │       ├── intents/intent.md
        │       ├── contexts/context.md
        │       ├── specs/spec.md
        │       ├── plans/plan.md
        │       ├── tasks/tasks.md
        │       ├── implementation/README.md
        │       ├── feedback/feedback.md
        │       └── metadata/.owner
        ├── CURRENT_SESSION
        └── session_state.json
```

### 2. Check Project Status

```bash
idse status
```

Output:
```
📊 IDSE Project Status

Project: customer-portal
Session: session-1736534123

Pipeline Stages:
  ⏳ intent         : pending
  ⏳ context        : pending
  ⏳ spec           : pending
  ⏳ plan           : pending
  ⏳ tasks          : pending
  ⏳ implementation : pending
  ⏳ feedback       : pending

⚠️  Validation: unknown
```

### 3. Validate Artifacts

```bash
idse validate
```

## Configuration

Create `~/.idseconfig.json`:

```json
{
  "auto_detect_stages": true
}
```

## Sync Backends

The orchestrator can sync artifacts via configured storage backends.

### Configure Sync

```bash
idse sync setup
```

### Notion Backend (MCP)

To use Notion as the Artifact Core backend, create an "IDSE Artifacts" database and configure:

```json
{
  "artifact_backend": "notion",
  "notion": {
    "database_id": "your-notion-database-id",
    "database_view_id": "optional-database-view-id",
    "database_view_url": "optional-database-view-url",
    "parent_data_source_url": "collection://your-data-source-id",
    "data_source_id": "your-data-source-id",
    "credentials_dir": "./mnt/mcp_credentials",
    "tool_names": {
      "query_database": "notion-query-database-view",
      "create_page": "notion-create-pages",
      "update_page": "notion-update-page",
      "fetch_page": "notion-fetch",
      "append_children": "append_block_children"
    },
    "properties": {
      "idse_id": { "name": "IDSE_ID", "type": "text" },
      "title": { "name": "Title", "type": "title" },
      "project": { "name": "Project", "type": "text" },
      "session": { "name": "Session", "type": "text" },
      "stage": { "name": "Stage", "type": "select" },
      "content": { "name": "body", "type": "page_body" }
    }
  }
}
```

Then run:

```bash
idse sync push
idse sync pull
idse sync status
idse sync test
idse sync tools
```

Stage values are normalized to Title Case (`Intent`, `Context`, `Specification`,
`Plan`, `Tasks`, `Test Plan`, `Feedback`) to match Notion select options.

## Commands

### `idse init <project-name>`

Initialize a new IDSE project with pipeline structure.

**Options:**
- `--stack`: Technology stack (python, node, go, etc.)

### `idse validate`

Validate pipeline artifacts for constitutional compliance.

**Checks:**
- All required sections present
- No `[REQUIRES INPUT]` markers
- Stage sequencing (Article III)
- Template compliance (Article IV)


### `idse status`

Display current project and session status.

## Architecture

### Project Structure

```
client-repo/
├── .idse/                  # IDSE workspace (gitignored)
│   └── projects/
│       └── <project-name>/
│           ├── sessions/
│           │   └── session-<timestamp>/
│           │       ├── intents/
│           │       ├── contexts/
│           │       ├── specs/
│           │       ├── plans/
│           │       ├── tasks/
│           │       ├── implementation/
│           │       ├── feedback/
│           │       └── metadata/
│           ├── CURRENT_SESSION
│           └── session_state.json
└── src/                    # Actual codebase
```

### State Tracking

The `session_state.json` tracks pipeline progression:

```json
{
  "project_name": "customer-portal",
  "session_id": "session-1736534123",
  "stages": {
    "intent": "complete",
    "context": "in_progress",
    "spec": "pending",
    "plan": "pending",
    "tasks": "pending",
    "implementation": "pending",
    "feedback": "pending"
  },
  "validation_status": "passing"
}
```

### Agent Coordination

The orchestrator routes tasks to IDE agents based on `agent_registry.json`:

```json
{
  "agents": [
    {
      "id": "claude-code",
      "stages": ["intent", "context", "spec", "plan", "tasks"]
    },
    {
      "id": "gpt-codex",
      "stages": ["implementation"]
    }
  ]
}
```

## Development

### Run Tests

```bash
pytest tests/
```

### Type Checking

```bash
mypy src/
```

### Code Formatting

```bash
black src/ tests/
```

## Self-Dogfooding

This repository uses its own IDSE pipeline structure:

```
.idse/
└── projects/
    └── idse-orchestrator/
        ├── sessions/
        │   └── __blueprint__/
        │       ├── intents/intent.md
        │       ├── contexts/context.md
        │       ├── specs/spec.md
        │       ├── plans/plan.md
        │       ├── tasks/tasks.md
        │       ├── implementation/README.md
        │       ├── feedback/feedback.md
        │       └── metadata/
        ├── CURRENT_SESSION
        └── session_state.json
```

To check project status:
```bash
idse status
idse validate
```

## License

MIT License - See LICENSE file for details

## Related Projects

- **IDSE Constitution**: Governance framework (Articles I-X)
- **Agency Swarm**: Multi-agent orchestration framework

## Support

For issues and questions:
- GitHub Issues: https://github.com/tjpilant/idse-orchestrator/issues
- Documentation: https://github.com/tjpilant/idse-orchestrator#readme
