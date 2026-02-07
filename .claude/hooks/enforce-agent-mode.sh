#!/bin/bash
# .claude/hooks/enforce-agent-mode.sh
# Enforces IDSE agent registry mode constraints
# Planning mode: can write pipeline docs (.idse/) and run tests, but not modify source code

# Read hook input from stdin
INPUT=$(cat)
TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name')

# Find the agent registry
REGISTRY=".idse/projects/idse-orchestrator/agent_registry.json"

if [ ! -f "$REGISTRY" ]; then
  exit 0  # No registry, allow all
fi

# Get claude-code agent's mode
MODE=$(jq -r '.agents[] | select(.id == "claude-code") | .mode' "$REGISTRY")

if [ "$MODE" = "planning" ]; then
  # --- Edit / Write: allow pipeline artifacts, block source code ---
  if [ "$TOOL_NAME" = "Edit" ] || [ "$TOOL_NAME" = "Write" ]; then
    FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // ""')
    if echo "$FILE_PATH" | grep -qE '\.idse/|CLAUDE\.md|\.claude/'; then
      exit 0  # Pipeline artifacts are planning work
    fi
    # Block writes to source code, tests, configs, etc.
    jq -n '{
      hookSpecificOutput: {
        hookEventName: "PreToolUse",
        permissionDecision: "deny",
        permissionDecisionReason: "BLOCKED: Planning mode cannot modify source files. Only .idse/ pipeline artifacts are writable. Hand off to an implementation agent for code changes."
      }
    }'
    exit 0
  fi

  # --- Bash: allow tests and read-only commands, block everything else ---
  if [ "$TOOL_NAME" = "Bash" ]; then
    COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // ""')
    # Allow: pytest, python -m pytest, test runners, read-only git, idse CLI
    if echo "$COMMAND" | grep -qE '^(PYTHONPATH=.*)?pytest|^python -m pytest|^idse |^git (status|log|diff|show|branch)'; then
      exit 0
    fi
    # Block other shell commands
    jq -n '{
      hookSpecificOutput: {
        hookEventName: "PreToolUse",
        permissionDecision: "deny",
        permissionDecisionReason: "BLOCKED: Planning mode allows only test runners (pytest), idse CLI, and read-only git. Hand off to an implementation agent for other commands."
      }
    }'
    exit 0
  fi

  # Allow all other tools (Read, Glob, Grep, etc.) — they are read-only
  exit 0
else
  exit 0  # Allow everything in implementation mode
fi
