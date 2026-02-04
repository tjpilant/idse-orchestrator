#!/bin/bash
# .claude/hooks/enforce-agent-mode.sh
# Enforces IDSE agent registry mode constraints

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
  # Block implementation tools in planning mode
  jq -n '{
    hookSpecificOutput: {
      hookEventName: "PreToolUse",
      permissionDecision: "deny",
      permissionDecisionReason: "BLOCKED: Your mode is \"planning\" per agent_registry.json. Implementation tools (Edit, Write, Bash) are not allowed. Hand off to an implementation agent or change your mode to \"implementation\"."
    }
  }'
else
  exit 0  # Allow in implementation mode
fi
