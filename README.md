# IDSE Developer Orchestrator

A pip-installable CLI tool for managing Intent-Driven Systems Engineering (IDSE) projects in client workspaces.

## Overview

The IDSE Orchestrator is **Layer 2** in the three-layer IDSE ecosystem:

```
Layer 1: Agency Core (Multi-tenant backend)
         ↕ MCP Sync
Layer 2: IDSE Orchestrator (This package - per client)
         ↕ Coordinates
Layer 3: IDE Agents (Claude Code, GPT Codex)
```

## Features

- **Project Initialization**: Generate complete IDSE pipeline structure with templates
- **Validation**: Check artifacts for constitutional compliance
- **State Tracking**: Monitor pipeline stage progression
- **MCP Sync**: Bidirectional sync with Agency Core backend
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
Last Sync: Never

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

### 4. Sync with Agency Core

```bash
# Configure Agency Core URL
export IDSE_AGENCY_URL=https://agency.example.com

# Push local changes
idse sync push

# Pull latest from server
idse sync pull
```

## Configuration

Create `~/.idseconfig.json`:

```json
{
  "agency_url": "https://agency.example.com",
  "client_id": "your-client-id",
  "auto_detect_stages": true
}
```

## Commands

### `idse init <project-name>`

Initialize a new IDSE project with pipeline structure.

**Options:**
- `--stack`: Technology stack (python, node, go, etc.)
- `--client-id`: Client ID from Agency Core

### `idse validate`

Validate pipeline artifacts for constitutional compliance.

**Checks:**
- All required sections present
- No `[REQUIRES INPUT]` markers
- Stage sequencing (Article III)
- Template compliance (Article IV)

### `idse sync push`

Upload local artifacts to Agency Core.

**Options:**
- `--project`: Project name (uses current if not specified)
- `--agency-url`: Agency Core URL (or use `IDSE_AGENCY_URL` env var)

### `idse sync pull`

Download latest artifacts from Agency Core.

**Options:**
- `--force`: Overwrite local changes without prompting

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
  "last_sync": "2026-01-10T12:34:56Z",
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

## License

MIT License - See LICENSE file for details

## Related Projects

- **IDSE Developer Agency**: Multi-tenant Agency Core backend
- **IDSE Constitution**: Governance framework (Articles I-X)
- **Agency Swarm**: Multi-agent orchestration framework

## Support

For issues and questions:
- GitHub Issues: https://github.com/idse-agency/idse-orchestrator/issues
- Documentation: https://docs.idse-agency.dev
