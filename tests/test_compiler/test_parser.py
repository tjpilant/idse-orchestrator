import pytest

from idse_orchestrator.compiler.parser import parse_agent_profile
from idse_orchestrator.compiler.errors import AgentProfileNotFound, InvalidAgentProfileYAML


def test_parse_agent_profile_ok():
    md = """
# Specification

## Agent Profile

```yaml
id: agent-1
name: Agent One
```
"""
    data = parse_agent_profile(md)
    assert data["id"] == "agent-1"


def test_parse_agent_profile_missing_section():
    with pytest.raises(AgentProfileNotFound):
        parse_agent_profile("# Spec")


def test_parse_agent_profile_invalid_yaml():
    md = """
## Agent Profile

```yaml
:bad
```
"""
    with pytest.raises(InvalidAgentProfileYAML):
        parse_agent_profile(md)
