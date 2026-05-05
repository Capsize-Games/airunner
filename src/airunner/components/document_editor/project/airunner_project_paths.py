"""Filesystem layout helpers for AIRunner coding projects."""

import os

PROJECT_DIR_NAME = ".airunner"
WORKSPACE_FILE = os.path.join(PROJECT_DIR_NAME, "workspace.json")
SETTINGS_FILE = os.path.join(PROJECT_DIR_NAME, "settings.json")
INSTRUCTIONS_FILE = os.path.join(
    PROJECT_DIR_NAME,
    "airunner-instructions.md",
)
PROMPT_TEMPLATES_DIR = os.path.join(
    PROJECT_DIR_NAME,
    "prompt_templates",
)
PROJECT_DIRECTORIES = (
    "agents",
    "audit",
    "indexes",
    "memory",
    "plans",
    "prompt_templates",
    "sessions",
    "tasks",
    "terminal",
)


def required_project_directories() -> list[str]:
    """Return the required .airunner directory paths."""
    return [
        os.path.join(PROJECT_DIR_NAME, directory)
        for directory in PROJECT_DIRECTORIES
    ]