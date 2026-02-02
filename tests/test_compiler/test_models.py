import pytest

from idse_orchestrator.compiler.models import AgentProfileSpec


def test_agent_profile_valid():
    spec = AgentProfileSpec(id="agent-1", name="Agent One")
    assert spec.id == "agent-1"


def test_agent_profile_missing_required():
    with pytest.raises(Exception):
        AgentProfileSpec(name="Agent One")
