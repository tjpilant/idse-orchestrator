"""Interactive wizard for populating blueprint documents"""
import click
from typing import Dict


class BlueprintWizard:
    """Interactive questionnaire for blueprint creation"""

    def run(self, project_name: str, stack: str) -> Dict[str, str]:
        """Run interactive questionnaire. Returns artifact dict."""

        click.echo("\n🎯 Let's create your project blueprint!")
        click.echo("Answer the following questions to populate your pipeline documents.\n")

        # Intent Questions
        click.echo("=== INTENT (What & Why) ===")
        vision = click.prompt("What is this project building?")
        problem = click.prompt("What problem does it solve?")
        success = click.prompt("How will you measure success?")

        # Context Questions
        click.echo("\n=== CONTEXT (Constraints & Environment) ===")
        constraints = click.prompt("What are the main constraints? (tech, budget, timeline)")
        assumptions = click.prompt("What assumptions are you making?")
        risks = click.prompt("What are the biggest risks?")

        # Spec Questions
        click.echo("\n=== SPECIFICATION (Requirements) ===")
        user_stories = click.prompt("Describe 2-3 key user stories")
        requirements = click.prompt("List top 3 functional requirements")

        # Plan Questions
        click.echo("\n=== PLAN (Architecture) ===")
        architecture = click.prompt("What's the high-level architecture? (frontend, backend, db)")
        phases = click.prompt("What are the implementation phases?")

        return {
            "intent_md": self._generate_intent(project_name, vision, problem, success),
            "context_md": self._generate_context(project_name, constraints, assumptions, risks),
            "spec_md": self._generate_spec(project_name, user_stories, requirements),
            "plan_md": self._generate_plan(project_name, architecture, phases),
            "tasks_md": self._generate_tasks_stub(project_name),
            "feedback_md": self._generate_feedback_stub(project_name),
            "implementation_readme_md": self._generate_implementation_stub(project_name)
        }

    def _generate_intent(self, project_name: str, vision: str, problem: str, success: str) -> str:
        return f"""# Intent: {project_name}

## Vision
{vision}

## Problem
{problem}

## Success Criteria
{success}

## Stakeholders
[To be filled]

## Constraints
[To be filled]

## Scope
[To be filled]
"""

    def _generate_context(self, project_name: str, constraints: str, assumptions: str, risks: str) -> str:
        return f"""# Context: {project_name}

## Constraints
{constraints}

## Assumptions
{assumptions}

## Risks
{risks}

## Environment
[To be filled]
"""

    def _generate_spec(self, project_name: str, user_stories: str, requirements: str) -> str:
        return f"""# Specification: {project_name}

## User Stories
{user_stories}

## Functional Requirements
{requirements}

## Non-Functional Requirements
[To be filled]

## Acceptance Criteria
[To be filled]
"""

    def _generate_plan(self, project_name: str, architecture: str, phases: str) -> str:
        return f"""# Plan: {project_name}

## Architecture
{architecture}

## Implementation Phases
{phases}

## Components
[To be filled]

## Data Model
[To be filled]
"""

    def _generate_tasks_stub(self, project_name: str) -> str:
        return f"""# Tasks: {project_name}

## Phase 0: Foundations
[ ] Task 0.1 - Setup project structure

## Phase 1: Core Features
[To be filled based on plan]

## Phase 2: Non-Functional Requirements
[To be filled]
"""

    def _generate_feedback_stub(self, project_name: str) -> str:
        return f"""# Feedback: {project_name}

## External Feedback
[To be filled as feedback is received]

## Internal Feedback
[To be filled]

## Actions
[To be filled]
"""

    def _generate_implementation_stub(self, project_name: str) -> str:
        return f"""# Implementation: {project_name}

This directory contains documentation about implementation progress.

## Architecture
[To be filled]

## Validation Reports
[To be filled]
"""
