"""Manage project-scoped instruction and prompt-template files."""

from __future__ import annotations

from dataclasses import dataclass
import os

from airunner.components.document_editor.project.airunner_active_project import (
    get_active_project_path,
)
from airunner.components.document_editor.project.airunner_project_paths import (
    INSTRUCTIONS_FILE,
    PROMPT_TEMPLATES_DIR,
)
from airunner.components.document_editor.project.airunner_project_service import (
    AirunnerProjectService,
)


@dataclass(frozen=True)
class AirunnerProjectPromptTemplate:
    """Describe one project-defined slash template."""

    command_name: str
    description: str
    prompt: str
    source_path: str


class AirunnerProjectPromptService:
    """Load AIRunner prompt files stored under .airunner/."""

    def __init__(self, project_service):
        self.project_service = project_service

    def ensure_defaults(self, bootstrap_profile: str | None = None) -> None:
        """Create the default project instruction and template files."""
        self._ensure_file(
            INSTRUCTIONS_FILE,
            self._instructions_content(bootstrap_profile),
        )
        self._ensure_file(
            os.path.join(PROMPT_TEMPLATES_DIR, "implement.prompt.md"),
            self._implement_template(),
        )
        self._ensure_file(
            os.path.join(PROMPT_TEMPLATES_DIR, "review.prompt.md"),
            self._review_template(),
        )
        self._ensure_file(
            os.path.join(PROMPT_TEMPLATES_DIR, "meeting-pack.prompt.md"),
            self._meeting_pack_template(),
        )
        self._ensure_file(
            os.path.join(PROMPT_TEMPLATES_DIR, "meeting-review.prompt.md"),
            self._meeting_review_template(),
        )

    def instructions_text(self) -> str:
        """Return the project instruction markdown body."""
        path = self.project_service.resolve_path(INSTRUCTIONS_FILE)
        if not os.path.exists(path):
            return ""
        return self.project_service.read_file(INSTRUCTIONS_FILE).strip()

    def prompt_templates(self) -> list[AirunnerProjectPromptTemplate]:
        """Return all project-defined slash templates."""
        directory = self.project_service.resolve_path(PROMPT_TEMPLATES_DIR)
        if not os.path.isdir(directory):
            return []
        templates: list[AirunnerProjectPromptTemplate] = []
        for name in sorted(os.listdir(directory)):
            template = self._read_template(name)
            if template is not None:
                templates.append(template)
        return templates

    def _ensure_file(self, rel_path: str, content: str) -> None:
        """Write one default file when it does not already exist."""
        path = self.project_service.resolve_path(rel_path)
        if os.path.exists(path):
            return
        self.project_service.write_file(rel_path, content, backup=False)

    def _read_template(
        self,
        file_name: str,
    ) -> AirunnerProjectPromptTemplate | None:
        """Read one prompt-template file from the project."""
        if not self._is_template_file(file_name):
            return None
        rel_path = os.path.join(PROMPT_TEMPLATES_DIR, file_name)
        raw = self.project_service.read_file(rel_path)
        description, prompt = self._parse_template_content(raw)
        prompt = prompt.strip()
        if not prompt:
            return None
        return AirunnerProjectPromptTemplate(
            command_name=self._template_command_name(file_name),
            description=description,
            prompt=prompt,
            source_path=self.project_service.resolve_path(rel_path),
        )

    def _is_template_file(self, file_name: str) -> bool:
        """Return whether a file should be exposed as a slash template."""
        lower_name = file_name.lower()
        return lower_name.endswith(".prompt.md") or lower_name.endswith(".md")

    def _template_command_name(self, file_name: str) -> str:
        """Return the slash command name for a template file."""
        if file_name.endswith(".prompt.md"):
            return file_name[:-10]
        return os.path.splitext(file_name)[0]

    def _parse_template_content(self, content: str) -> tuple[str, str]:
        """Parse optional frontmatter and return description plus body."""
        if not content.startswith("---\n"):
            return "Project prompt template", content
        parts = content.split("\n---\n", 1)
        if len(parts) != 2:
            return "Project prompt template", content
        description = "Project prompt template"
        for line in parts[0][4:].splitlines():
            key, _, value = line.partition(":")
            if key.strip().lower() == "description" and value.strip():
                description = value.strip()
        return description, parts[1]

    def _instructions_content(
        self,
        bootstrap_profile: str | None,
    ) -> str:
        """Return default project instructions for new workspaces."""
        python_block = ""
        if bootstrap_profile == "python-package":
            python_block = (
                "\n## Python\n"
                "- Follow PEP 8 and keep lines at 80 characters or less.\n"
                "- Use type hints and docstrings for new public code.\n"
                "- Add or update tests when behavior changes.\n"
            )
        return (
            "# AIRunner Instructions\n\n"
            "Use this file for project-specific coding guidance that should be "
            "appended to the Code Agent system prompt.\n\n"
            "## General\n"
            "- Keep changes focused on the current task.\n"
            "- Preserve existing conventions unless the task requires a "
            "change.\n"
            "- Validate modified behavior before declaring the task done.\n"
            "\n## Meeting Workflows\n"
            "- Use /meeting-pack to turn meeting notes or transcripts into "
            "deliverable packs.\n"
            "- Use /meeting-review to inspect flagged items, apply "
            "corrections, and approve packs.\n"
            "- Keep meeting artifacts under .airunner/meetings and open "
            "generated markdown in the document editor for review.\n"
            f"{python_block}"
        )

    def _implement_template(self) -> str:
        """Return the default implementation template content."""
        return (
            "---\n"
            "description: Implement the requested feature in this project\n"
            "---\n"
            "Inspect the relevant files before editing. Keep changes minimal, "
            "update tests when behavior changes, and summarize what was "
            "implemented plus how it was validated.\n"
        )

    def _review_template(self) -> str:
        """Return the default review template content."""
        return (
            "---\n"
            "description: Review a change for bugs, regressions, and gaps\n"
            "---\n"
            "Review the relevant files with a code-review mindset. Prioritize "
            "concrete bugs, regressions, risky assumptions, and missing tests.\n"
        )

    def _meeting_pack_template(self) -> str:
        """Return the default meeting-pack workflow template."""
        return (
            "---\n"
            "description: Turn meeting input into a deliverable pack\n"
            "---\n"
            "Treat this as a meeting-to-deliverables workflow in the active "
            "AIRunner project. Start or update a meeting run, record the "
            "structured decisions, tasks, risks, deadlines, and open "
            "questions, generate the meeting pack, open the pack in the "
            "document editor, and call out unresolved items that still need "
            "review.\n"
        )

    def _meeting_review_template(self) -> str:
        """Return the default meeting-review workflow template."""
        return (
            "---\n"
            "description: Review and approve the latest meeting pack\n"
            "---\n"
            "Inspect the latest meeting deliverable pack, surface the flagged "
            "or low-confidence items, apply any user corrections, persist the "
            "review result, open the review artifact in the document editor, "
            "and report whether the pack is approved or still needs revision.\n"
        )


def active_project_prompt_service() -> AirunnerProjectPromptService | None:
    """Return a prompt service for the active coding project."""
    project_path = get_active_project_path()
    if not project_path:
        return None
    project_service = AirunnerProjectService(project_path)
    if not project_service.exists():
        return None
    return AirunnerProjectPromptService(project_service)