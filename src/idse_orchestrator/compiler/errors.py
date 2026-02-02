class CompilerError(Exception):
    """Base compiler error."""


class AgentProfileNotFound(CompilerError):
    """Agent Profile section not found in spec."""


class InvalidAgentProfileYAML(CompilerError):
    """Invalid YAML in Agent Profile section."""


class ValidationError(CompilerError):
    """Model validation failed."""
