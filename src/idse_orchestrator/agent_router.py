"""
Agent Router

Routes work between IDE agents (Claude Code, GPT Codex) based on
pipeline stages and agent registry.
"""

import json
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime


class AgentRouter:
    """Routes tasks to appropriate IDE agents based on stage and registry."""

    def __init__(self, registry_path: Optional[Path] = None):
        """
        Initialize AgentRouter.

        Args:
            registry_path: Path to agent_registry.json. Defaults to packaged registry.
        """
        if registry_path is None:
            registry_path = Path(__file__).parent.parent / "config" / "agent_registry.json"

        self.registry_path = registry_path
        self.registry = self._load_registry()

    def get_agent_for_stage(self, stage: str) -> Optional[str]:
        """
        Get recommended agent for a given pipeline stage.

        Args:
            stage: Pipeline stage name (intent, context, spec, plan, tasks, implementation, feedback)

        Returns:
            Agent ID or None if no agent handles this stage
        """
        for agent in self.registry.get("agents", []):
            if stage in agent.get("stages", []):
                return agent["id"]

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

        # Log assignment
        self.log_assignment("orchestrator", agent_id, stage)

        return handoff

    def log_assignment(self, from_agent: str, to_agent: str, stage: str) -> None:
        """
        Log agent assignment for audit trail.

        Args:
            from_agent: Source agent ID
            to_agent: Destination agent ID
            stage: Pipeline stage
        """
        # TODO: Implement assignment logging to file
        print(f"Assignment: {from_agent} → {to_agent} ({stage})")

    def handoff_to_agent(self, stage: str, context: Dict) -> Dict:
        """
        Deprecated: use route_to_agent instead.
        """
        return self.route_to_agent(stage, context)

    def log_handoff(self, from_agent: str, to_agent: str, stage: str) -> None:
        """
        Deprecated: use log_assignment instead.
        """
        self.log_assignment(from_agent, to_agent, stage)

    def _load_registry(self) -> Dict:
        """
        Load agent registry from JSON file.

        Returns:
            Registry dictionary
        """
        if not self.registry_path.exists():
            # Return default registry
            return {
                "agents": [
                    {
                        "id": "claude-code",
                        "role": "orchestrator",
                        "stages": ["intent", "context", "spec", "plan", "tasks"],
                    },
                    {"id": "gpt-codex", "role": "implementer", "stages": ["implementation"]},
                ]
            }

        with self.registry_path.open("r") as f:
            return json.load(f)
