import json
from pathlib import Path

from idse_orchestrator.agent_registry import AgentRegistry


def test_agent_registry_load_and_query(tmp_path: Path):
    registry_path = tmp_path / "agent_registry.json"
    data = {
        "agents": [
            {"id": "a1", "stages": ["intent"]},
            {"id": "a2", "stages": ["implementation"]},
        ]
    }
    registry_path.write_text(json.dumps(data))

    registry = AgentRegistry(registry_path=registry_path)

    assert registry.get_agent("a1")["id"] == "a1"
    assert registry.get_agents_for_stage("intent")[0]["id"] == "a1"


def test_agent_registry_register(tmp_path: Path):
    registry_path = tmp_path / "agent_registry.json"
    registry = AgentRegistry(registry_path=registry_path)

    registry.register_agent({"id": "new", "stages": ["plan"]})
    registry2 = AgentRegistry(registry_path=registry_path)

    assert any(a["id"] == "new" for a in registry2.list_agents())
