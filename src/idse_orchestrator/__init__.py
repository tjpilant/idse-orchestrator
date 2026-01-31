"""
IDSE Developer Orchestrator

A pip-installable CLI package for managing Intent-Driven Systems Engineering (IDSE)
projects in client workspaces. This orchestrator coordinates IDE agents (Claude Code,
GPT Codex) and syncs pipeline artifacts with the Agency Core backend.

Architecture:
- Layer 2 in the three-layer IDSE ecosystem
- Installed per client workspace via pip
- Generates pipeline docs from templates
- Tracks session state and stage progress
- Coordinates agent routing across IDE agents when configured
- Syncs with Agency Core via MCP protocol
"""

__version__ = "0.1.0"
__author__ = "IDSE Developer Agency"
__license__ = "MIT"

# Public API
from .cli import main

__all__ = ["main"]
