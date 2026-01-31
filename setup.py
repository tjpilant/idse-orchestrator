"""
Setup configuration for IDSE Developer Orchestrator package.
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read README for long description
readme_file = Path(__file__).parent / "README.md"
long_description = readme_file.read_text() if readme_file.exists() else ""

# Read requirements
requirements_file = Path(__file__).parent / "requirements.txt"
requirements = (
    requirements_file.read_text().strip().split("\n") if requirements_file.exists() else []
)

setup(
    name="idse-orchestrator",
    version="0.1.0",
    author="IDSE Developer Agency",
    author_email="noreply@idse-agency.dev",
    description="CLI tool for managing Intent-Driven Systems Engineering (IDSE) projects",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/idse-agency/idse-orchestrator",
    project_urls={
        "Documentation": "https://docs.idse-agency.dev",
        "Source": "https://github.com/idse-agency/idse-orchestrator",
    },
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    include_package_data=True,
    package_data={
        "idse_orchestrator": [
            "config/*.json",
            "resources/docs/*.md",
            "resources/templates/*.md",
            "templates/agent_instructions/*",
            "resources/frameworks/agency-swarm/.cursor/rules/*.mdc",
            "resources/frameworks/agency-swarm/.cursor/rules/*",
            "resources/frameworks/agency-swarm/.cursor/commands/*.md",
            "resources/frameworks/agency-swarm/.claude/*",
            "resources/frameworks/agency-swarm/.claude/agents/*",
            "governance/*.md",
        ],
    },
    install_requires=requirements,
    python_requires=">=3.8",
    entry_points={
        "console_scripts": [
            "idse=idse_orchestrator.cli:main",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Build Tools",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    keywords="idse development pipeline orchestration cli",
)
