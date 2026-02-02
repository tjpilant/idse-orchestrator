from __future__ import annotations

import re
from typing import Dict
import yaml

from .errors import AgentProfileNotFound, InvalidAgentProfileYAML


AGENT_PROFILE_HEADING = "## Agent Profile"


def parse_agent_profile(markdown: str) -> Dict:
    """Extract the first YAML code block under ## Agent Profile heading."""
    if AGENT_PROFILE_HEADING not in markdown:
        raise AgentProfileNotFound("Agent Profile section not found")

    # Find heading position
    heading_index = markdown.find(AGENT_PROFILE_HEADING)
    section = markdown[heading_index:]

    # Find first fenced YAML block after heading
    match = re.search(r"```yaml\s*(.*?)```", section, re.DOTALL | re.IGNORECASE)
    if not match:
        raise AgentProfileNotFound("Agent Profile YAML block not found")

    yaml_text = match.group(1).strip()
    if not yaml_text:
        raise InvalidAgentProfileYAML("Agent Profile YAML block is empty")

    try:
        data = yaml.safe_load(yaml_text)
    except yaml.YAMLError as exc:
        raise InvalidAgentProfileYAML(str(exc)) from exc

    if not isinstance(data, dict):
        raise InvalidAgentProfileYAML("Agent Profile YAML must be a mapping")

    return data
