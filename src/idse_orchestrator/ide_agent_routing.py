"""
IDE Agent Routing

Routes work between IDE agents (Claude Code, GPT Codex) based on
pipeline stages and agent registry.
"""

from __future__ import annotations

from typing import Dict, Optional
from datetime import datetime

from .agent_registry import AgentRegistry


class IDEAgentRouting:
    """Routes tasks to appropriate IDE agents based on stage and registry."""

    def __init__(self, registry_path: Optional[str] = None):
        self.registry = AgentRegistry(registry_path)

    def get_agent_for_stage(self, stage: str) -> Optional[str]:
        agents = self.registry.get_agents_for_stage(stage)
        if agents:
            return agents[0]["id"]
        return None

    def route_to_agent(self, stage: str, context: Dict) -> Dict:
        """
        Prepare an assignment message for the selected agent.

        Args:
            stage: Target stage
            context: Context dictionary with project info and current state

        Returns:
            Assignment message dictionary
        """
        agent_id = self.get_agent_for_stage(stage)

        if not agent_id:
            raise ValueError(f"No agent found for stage: {stage}")

        handoff = {
            "to_agent": agent_id,
            "stage": stage,
            "timestamp": datetime.now().isoformat(),
            "context": context,
            "instructions": f"Please handle {stage} stage for project: {context.get('project_name')}",
        }

        self.log_assignment("orchestrator", agent_id, stage)

        return handoff

    def log_assignment(self, from_agent: str, to_agent: str, stage: str) -> None:
        """Log agent assignment for audit trail."""
        print(f"Assignment: {from_agent} -> {to_agent} ({stage})")

    def handoff_to_agent(self, stage: str, context: Dict) -> Dict:
        """Deprecated: use route_to_agent instead."""
        return self.route_to_agent(stage, context)

    def log_handoff(self, from_agent: str, to_agent: str, stage: str) -> None:
        """Deprecated: use log_assignment instead."""
        self.log_assignment(from_agent, to_agent, stage)
