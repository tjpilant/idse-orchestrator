from __future__ import annotations

import json
from pathlib import Path
from typing import Optional, List, Dict


class AgentRegistry:
    PIPELINE_STAGES = ["intent", "context", "spec", "plan", "tasks", "implementation", "feedback"]

    def __init__(self, registry_path: Optional[Path] = None):
        if registry_path is None:
            registry_path = Path(__file__).parent.parent / "config" / "agent_registry.json"
        self.registry_path = registry_path
        self._registry = self._load()

    def list_agents(self) -> List[Dict]:
        return list(self._registry.get("agents", []))

    def get_agent(self, agent_id: str) -> Dict:
        for agent in self._registry.get("agents", []):
            if agent.get("id") == agent_id:
                return agent
        raise KeyError(f"Agent not found: {agent_id}")

    def get_agents_for_stage(self, stage: str) -> List[Dict]:
        if stage not in self.PIPELINE_STAGES:
            raise ValueError(f"Unknown stage: {stage}")
        return [a for a in self._registry.get("agents", []) if stage in a.get("stages", [])]

    def register_agent(self, agent_spec: Dict) -> None:
        agents = self._registry.setdefault("agents", [])
        agents.append(agent_spec)
        self._persist()

    def _load(self) -> Dict:
        if not self.registry_path.exists():
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

    def _persist(self) -> None:
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)
        with self.registry_path.open("w") as f:
            json.dump(self._registry, f, indent=2)
