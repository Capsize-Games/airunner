"""Agent templates for common agent configurations."""

from typing import Dict, List


class AgentTemplate:
    """Agent template definition.

    Attributes:
        name: Template name identifier
        description: What this agent specializes in
        system_prompt: Default system prompt for template
        tools: Recommended tools for this agent type
    """

    def __init__(
        self,
        name: str,
        description: str,
        system_prompt: str,
        tools: List[str],
    ):
        """Initialize agent template.

        Args:
            name: Template name
            description: Template description
            system_prompt: Default system prompt
            tools: List of recommended tool names
        """
        self.name = name
        self.description = description
        self.system_prompt = system_prompt
        self.tools = tools

    def to_dict(self) -> Dict:
        """Convert template to dictionary.

        Returns:
            Dictionary representation
        """
        return {
            "name": self.name,
            "description": self.description,
            "system_prompt": self.system_prompt,
            "tools": self.tools,
        }


# Predefined agent templates
AGENT_TEMPLATES: Dict[str, AgentTemplate] = {
    "coding": AgentTemplate(
        name="coding",
        description="Expert coding assistant for software development",
        system_prompt=(
            "You are an expert software engineer specialized in writing clean, "
            "maintainable code. You follow best practices, write comprehensive "
            "tests, and provide clear documentation. You understand multiple "
            "programming languages and frameworks."
        ),
        tools=[
            "read_file",
            "write_file",
            "list_directory",
            "search_files",
            "run_command",
        ],
    ),
    "research": AgentTemplate(
        name="research",
        description="Research assistant for finding and analyzing information",
        system_prompt=(
            "You are a skilled research assistant who excels at finding accurate "
            "information, analyzing sources, and presenting findings clearly. "
            "You verify facts, cite sources, and provide comprehensive summaries."
        ),
        tools=[
            "search_web",
            "read_file",
            "search_files",
            "recall_knowledge",
            "extract_knowledge",
        ],
    ),
    "creative": AgentTemplate(
        name="creative",
        description="Creative writing and content generation specialist",
        system_prompt=(
            "You are a creative writing specialist skilled in storytelling, "
            "content creation, and artistic expression. You adapt your style "
            "to different genres and audiences while maintaining engaging, "
            "original content."
        ),
        tools=[
            "generate_image",
            "write_file",
            "read_file",
            "search_files",
        ],
    ),
    "calendar": AgentTemplate(
        name="calendar",
        description="Calendar and scheduling expert",
        system_prompt=(
            "You are a professional scheduling assistant who helps manage "
            "calendars, organize events, and coordinate schedules efficiently. "
            "You understand time zones, handle recurring events, and provide "
            "proactive reminders."
        ),
        tools=[
            "create_event",
            "list_events",
            "update_event",
            "delete_event",
            "create_reminder",
            "list_reminders",
        ],
    ),
    "custom": AgentTemplate(
        name="custom",
        description="Custom agent with user-defined configuration",
        system_prompt=(
            "You are a helpful AI assistant. Follow the user's instructions "
            "carefully and provide accurate, relevant responses."
        ),
        tools=[],
    ),
}


def get_template(name: str) -> AgentTemplate:
    """Get agent template by name.

    Args:
        name: Template name

    Returns:
        AgentTemplate instance

    Raises:
        KeyError: If template not found
    """
    if name not in AGENT_TEMPLATES:
        raise KeyError(
            f"Template '{name}' not found. "
            f"Available: {list(AGENT_TEMPLATES.keys())}"
        )
    return AGENT_TEMPLATES[name]


def list_templates() -> List[AgentTemplate]:
    """List all available templates.

    Returns:
        List of AgentTemplate instances
    """
    return list(AGENT_TEMPLATES.values())


def template_exists(name: str) -> bool:
    """Check if template exists.

    Args:
        name: Template name

    Returns:
        True if template exists
    """
    return name in AGENT_TEMPLATES
