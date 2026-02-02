"""Constitution rules for IDSE validation."""

PIPELINE_STAGES = ["intent", "context", "spec", "plan", "tasks", "implementation", "feedback"]

REQUIRED_SECTIONS = {
    "intent.md": ["Purpose / Goal", "Problem / Opportunity", "Vision", "Stakeholders", "Success Criteria"],
    "context.md": ["Environment Overview", "Technical Context", "Organizational Context"],
    "spec.md": ["Purpose", "System Overview", "Functional Requirements"],
    "plan.md": ["Architectural Overview", "Core Components", "Data Flow"],
    "tasks.md": ["Phase"],
}


def get_rules() -> dict:
    return {
        "required_sections": REQUIRED_SECTIONS,
        "pipeline_stages": PIPELINE_STAGES,
    }
