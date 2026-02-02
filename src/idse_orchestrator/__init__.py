"""
IDSE Developer Orchestrator

A pip-installable CLI package for managing Intent-Driven Systems Engineering (IDSE)
projects in client workspaces. This orchestrator coordinates IDE agents (Claude Code,
GPT Codex) and manages pipeline artifacts locally.

Architecture:
- Standalone per-workspace tool, installed via pip
- Generates pipeline docs from templates
- Tracks session state and stage progress
- Coordinates agent routing across IDE agents when configured
- CMS-agnostic storage via DesignStore abstraction
"""

__version__ = "0.1.0"
__author__ = "IDSE Developer Agency"
__license__ = "MIT"

# Public API
from .cli import main

__all__ = ["main"]
