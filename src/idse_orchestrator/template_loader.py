"""
Template Loader

Loads IDSE pipeline templates and performs substitutions while preserving
[REQUIRES INPUT] markers for user completion.
"""

from pathlib import Path
from typing import Dict, Optional
from jinja2 import Environment, FileSystemLoader, select_autoescape
from datetime import datetime


class TemplateLoader:
    """Loads and processes IDSE pipeline templates."""

    def __init__(self, templates_dir: Optional[Path] = None):
        """
        Initialize TemplateLoader.

        Args:
            templates_dir: Path to templates directory. If None, uses packaged templates.
        """
        if templates_dir is None:
            # Try multiple locations for templates
            possible_paths = [
                # Development: Same repo as Agency Core
                Path(__file__).parent.parent.parent.parent / "docs" / "kb" / "templates",
                # Installed package: bundled templates
                Path(__file__).parent / "templates",
                # User override
                Path.home() / ".idse" / "templates",
            ]

            for path in possible_paths:
                if path.exists() and list(path.glob("*.md")):
                    templates_dir = path
                    break
            else:
                # No templates found - will use placeholders only
                templates_dir = None

        self.templates_dir = templates_dir

        # Initialize Jinja2 environment only if templates exist
        if self.templates_dir:
            self.env = Environment(
                loader=FileSystemLoader(str(templates_dir)),
                autoescape=select_autoescape(),
                keep_trailing_newline=True,
            )
            # Preserve [REQUIRES INPUT] markers
            self.env.filters["preserve_markers"] = lambda x: x
        else:
            self.env = None

    def load_template(self, template_name: str, **context) -> str:
        """
        Load and render a single template.

        Args:
            template_name: Name of template file (e.g., "intent-template.md")
            **context: Variables to substitute in template

        Returns:
            Rendered template content
        """
        template = self.env.get_template(template_name)
        return template.render(**context)

    def load_all_templates(self, project_name: str, stack: str = "python") -> Dict[str, str]:
        """
        Load all IDSE pipeline templates with substitutions.

        Args:
            project_name: Name of the project
            stack: Technology stack

        Returns:
            Dictionary mapping template names to rendered content
        """
        context = {
            "project_name": project_name,
            "stack": stack,
            "timestamp": datetime.now().isoformat(),
            "date": datetime.now().strftime("%Y-%m-%d"),
        }

        templates = {
            "intent.md": "intent-template.md",
            "context.md": "context-template.md",
            "spec.md": "spec-template.md",
            "plan.md": "plan-template.md",
            "tasks.md": "tasks-template.md",
            "feedback.md": "feedback-template.md",
            "implementation_readme.md": "implementation-scaffold.md",
        }

        artifacts = {}

        for artifact_name, template_file in templates.items():
            template_path = self.templates_dir / template_file

            if template_path.exists():
                # For now, just read raw content (Jinja2 substitution will be added later)
                # This preserves [REQUIRES INPUT] markers
                artifacts[artifact_name] = self._load_raw_template(template_path, context)
            else:
                # Create minimal placeholder if template doesn't exist
                artifacts[artifact_name] = self._create_placeholder(artifact_name, context)

        return artifacts

    def _load_raw_template(self, template_path: Path, context: Dict) -> str:
        """
        Load template with minimal substitution.

        Args:
            template_path: Path to template file
            context: Substitution context

        Returns:
            Template content with basic substitutions
        """
        content = template_path.read_text()

        # Simple string substitution for now (can use Jinja2 later)
        content = content.replace("{{project_name}}", context["project_name"])
        content = content.replace("{{stack}}", context["stack"])
        content = content.replace("{{timestamp}}", context["timestamp"])
        content = content.replace("{{date}}", context["date"])

        return content

    def _create_placeholder(self, artifact_name: str, context: Dict) -> str:
        """
        Create a placeholder artifact if template doesn't exist.

        Args:
            artifact_name: Name of artifact (e.g., "intent.md")
            context: Substitution context

        Returns:
            Placeholder content
        """
        return f"""# {artifact_name.replace('.md', '').replace('_', ' ').title()}

Project: {context['project_name']}
Stack: {context['stack']}
Created: {context['timestamp']}

[REQUIRES INPUT]

This artifact was automatically generated but no template was found.
Please populate this document according to IDSE guidelines.
"""
