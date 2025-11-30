"""Agent management tools for ToolRegistry.

This module provides tools for creating, configuring, and managing custom AI
agents. Agents can be created with different templates (coding, research,
creative, calendar) and configured with specific system prompts and tools.

Tools:
    - create_agent: Create a new custom AI agent
    - configure_agent: Modify existing agent configuration
    - list_agents: List all available agents
    - delete_agent: Delete an agent by ID
    - get_agent: Get detailed agent configuration
    - list_agent_templates: List available agent templates

Examples:
    >>> # Create a coding agent
    >>> create_agent(
    ...     name="code_helper",
    ...     system_prompt="You are a Python expert.",
    ...     template="coding"
    ... )
    "Created agent 'code_helper' (ID: 1) using template 'coding' with 3 tools"

    >>> # List all agents
    >>> list_agents()
    "Available agents:\\n  [1] code_helper (active) - coding template - 3 tools"
"""

import json
from typing import Optional, List

from airunner.components.llm.core.tool_registry import tool, ToolCategory
from airunner.components.agents.data.agent_config import AgentConfig
from airunner.components.agents.templates import (
    get_template,
    list_templates,
    template_exists,
)
from airunner.components.data.session_manager import session_scope


@tool(
    name="create_agent",
    category=ToolCategory.SYSTEM,
    description=(
        "Create a new custom AI agent with specified name, system prompt, "
        "and available tools. Optionally use a template (coding, research, "
        "creative, calendar) to pre-configure the agent."
    ),
    requires_api=False,
)
def create_agent(
    name: str,
    system_prompt: str,
    description: Optional[str] = None,
    tools: Optional[List[str]] = None,
    template: str = "custom",
) -> str:
    """Create a new custom AI agent with specified configuration.

    This tool allows creating specialized AI agents with custom system prompts,
    descriptions, and tool access. Agents can be created from templates
    (coding, research, creative, calendar) or fully customized.

    Args:
        name: Unique agent name identifier (required)
        system_prompt: Custom system prompt for the agent (required)
        description: Description of agent purpose (optional)
        tools: List of tool names available to agent (optional)
        template: Template category - coding, research, creative, calendar,
            or custom. Defaults to "custom"


    Examples:
        >>> # Create a coding agent with template
        >>> create_agent(
        ...     name="python_expert",
        ...     system_prompt="You are a Python programming expert.",
        ...     template="coding"
        ... )
        "Created agent 'python_expert' (ID: 1) using template 'coding' with 3 tools"

        >>> # Create a custom agent with specific tools
        >>> create_agent(
        ...     name="research_bot",
        ...     system_prompt="You help with research tasks.",
        ...     description="Research assistant",
        ...     tools=["search_web", "scrape_website", "rag_search"],
        ...     template="custom"
        ... )
        "Created agent 'research_bot' (ID: 2) using template 'custom' with 3 tools"

    Note:
        - Agent names must be unique
        - Templates provide pre-configured system prompts and tools
        - Custom values override template defaults
        - Tools list can be empty (agent will use default tools)
    """
    try:
        # Validate template
        if template and not template_exists(template):
            return (
                f"Error: Template '{template}' not found. "
                f"Available templates: "
                f"{', '.join([t.name for t in list_templates()])}"
            )

        # Check if agent name already exists
        with session_scope() as session:
            existing = (
                session.query(AgentConfig)
                .filter(AgentConfig.name == name)
                .first()
            )
            if existing:
                return (
                    f"Error: Agent with name '{name}' already exists "
                    f"(ID: {existing.id})"
                )

        # If using template, merge template values with provided values
        if template and template != "custom":
            tmpl = get_template(template)
            # Use template system_prompt if not provided
            if not system_prompt or system_prompt == "":
                system_prompt = tmpl.system_prompt
            # Use template tools if not provided
            if not tools:
                tools = tmpl.tools
            # Use template description if not provided
            if not description:
                description = tmpl.description

        # Create agent
        agent = AgentConfig(
            name=name,
            description=description,
            system_prompt=system_prompt,
            template=template,
        )
        agent.tool_list = tools or []

        with session_scope() as session:
            session.add(agent)
            session.flush()
            agent_id = agent.id

        tool_count = len(tools) if tools else 0
        return (
            f"Created agent '{name}' (ID: {agent_id}) "
            f"using template '{template}' with {tool_count} tools"
        )
    except Exception as e:
        return f"Error creating agent: {str(e)}"


@tool(
    name="configure_agent",
    category=ToolCategory.SYSTEM,
    description=(
        "Modify an existing agent's configuration including name, "
        "description, system prompt, or available tools."
    ),
    requires_api=False,
)
def configure_agent(
    agent_id: int,
    name: Optional[str] = None,
    description: Optional[str] = None,
    system_prompt: Optional[str] = None,
    tools: Optional[List[str]] = None,
) -> str:
    """Modify an existing agent's configuration.

    This tool allows updating any aspect of an existing agent including its
    name, description, system prompt, or available tools.

    Args:
        agent_id: ID of agent to modify (required)
        name: New agent name (optional)
        description: New description (optional)
        system_prompt: New system prompt (optional)
        tools: New tool list (optional)


    Examples:
        >>> # Update agent name
        >>> configure_agent(agent_id=1, name="python_guru")
        "Updated agent 'python_guru' (ID: 1): name='python_guru'"

        >>> # Update system prompt and tools
        >>> configure_agent(
        ...     agent_id=1,
        ...     system_prompt="You are an expert Python developer.",
        ...     tools=["execute_python", "search_web"]
        ... )
        "Updated agent 'python_guru' (ID: 1): system_prompt, tools (2 items)"

    Note:
        - At least one field must be provided to update
        - Agent names must remain unique
        - Tools list replaces existing tools (not merge)
        - Returns list of changed fields
    """
    try:
        with session_scope() as session:
            agent = (
                session.query(AgentConfig)
                .filter(AgentConfig.id == agent_id)
                .first()
            )

            if not agent:
                return f"Error: Agent with ID {agent_id} not found"

            # Track changes
            changes = []

            if name is not None:
                # Check if new name already exists
                existing = (
                    session.query(AgentConfig)
                    .filter(
                        AgentConfig.name == name,
                        AgentConfig.id != agent_id,
                    )
                    .first()
                )
                if existing:
                    return (
                        f"Error: Agent with name '{name}' "
                        f"already exists (ID: {existing.id})"
                    )
                agent.name = name
                changes.append(f"name='{name}'")

            if description is not None:
                agent.description = description
                changes.append("description")

            if system_prompt is not None:
                agent.system_prompt = system_prompt
                changes.append("system_prompt")

            if tools is not None:
                agent.tool_list = tools
                changes.append(f"tools ({len(tools)} items)")

            session.flush()

            if not changes:
                return f"No changes made to agent '{agent.name}'"

            return (
                f"Updated agent '{agent.name}' (ID: {agent_id}): "
                f"{', '.join(changes)}"
            )
    except Exception as e:
        return f"Error configuring agent: {str(e)}"


@tool(
    name="list_agents",
    category=ToolCategory.SYSTEM,
    description=(
        "List all available custom agents with their IDs, names, "
        "descriptions, and tool counts."
    ),
    requires_api=False,
)
def list_agents(
    active_only: bool = True, template: Optional[str] = None
) -> str:
    """List all available custom agents.

    This tool displays all configured agents with their IDs, names,
    descriptions, template types, and tool counts. Can filter by active
    status and template type.

    Args:
        active_only: Only show active agents. Defaults to True
        template: Filter by template type (optional)


    Examples:
        >>> # List all active agents
        >>> list_agents()
        "Available agents:\\n  [1] python_expert (active) - coding template - 3 tools\\n      Python programming expert"

        >>> # List all agents including inactive
        >>> list_agents(active_only=False)
        "Available agents:\\n  [1] python_expert (active) - coding template - 3 tools\\n  [2] old_bot (inactive) - custom template - 0 tools"

        >>> # List agents by template
        >>> list_agents(template="coding")
        "Available agents:\\n  [1] python_expert (active) - coding template - 3 tools"

    Note:
        - Agents are ordered by creation date (newest first)
        - Shows agent status (active/inactive)
        - Includes description if available
        - Returns "No agents found" if none match criteria
    """
    try:
        with session_scope() as session:
            query = session.query(AgentConfig)

            if active_only:
                query = query.filter(AgentConfig.is_active == 1)

            if template:
                query = query.filter(AgentConfig.template == template)

            agents = query.order_by(AgentConfig.created_at.desc()).all()

            if not agents:
                return "No agents found"

            lines = ["Available agents:"]
            for agent in agents:
                tool_count = len(agent.tool_list)
                status = "active" if agent.is_active else "inactive"
                lines.append(
                    f"  [{agent.id}] {agent.name} ({status}) - "
                    f"{agent.template} template - "
                    f"{tool_count} tools"
                )
                if agent.description:
                    lines.append(f"      {agent.description}")

            return "\n".join(lines)
    except Exception as e:
        return f"Error listing agents: {str(e)}"


@tool(
    name="delete_agent",
    category=ToolCategory.SYSTEM,
    description="Delete a custom agent by ID",
    requires_api=False,
)
def delete_agent(agent_id: int) -> str:
    """Delete a custom agent by ID.

    This tool permanently removes an agent from the database. This action
    cannot be undone.

    Args:
        agent_id: ID of agent to delete (required)


    Examples:
        >>> # Delete an agent
        >>> delete_agent(agent_id=2)
        "Deleted agent 'old_bot' (ID: 2)"

        >>> # Try to delete non-existent agent
        >>> delete_agent(agent_id=999)
        "Error: Agent with ID 999 not found"

    Warning:
        - This action is permanent and cannot be undone
        - Agent will be immediately removed from database
        - Any references to this agent will become invalid
    """
    try:
        with session_scope() as session:
            agent = (
                session.query(AgentConfig)
                .filter(AgentConfig.id == agent_id)
                .first()
            )

            if not agent:
                return f"Error: Agent with ID {agent_id} not found"

            agent_name = agent.name
            session.delete(agent)
            session.flush()

            return f"Deleted agent '{agent_name}' (ID: {agent_id})"
    except Exception as e:
        return f"Error deleting agent: {str(e)}"


@tool(
    name="get_agent",
    category=ToolCategory.SYSTEM,
    description="Get detailed configuration for a specific agent by ID",
    requires_api=False,
)
def get_agent(agent_id: int) -> str:
    """Get detailed configuration for a specific agent.

    This tool retrieves the complete configuration of an agent including
    all settings, tools, and metadata in JSON format.

    Args:
        agent_id: ID of agent to retrieve (required)


    Examples:
        >>> # Get agent details
        >>> get_agent(agent_id=1)
        '{\\n  "id": 1,\\n  "name": "python_expert",\\n  "description": "Python programming expert",\\n  "system_prompt": "You are a Python expert.",\\n  "template": "coding",\\n  "tools": ["execute_python", "search_web", "rag_search"],\\n  "is_active": true,\\n  "created_at": "2025-11-01T10:00:00"\\n}'

    Note:
        - Returns complete agent configuration
        - Output is JSON formatted for easy parsing
        - Includes all fields and metadata
    """
    try:
        with session_scope() as session:
            agent = (
                session.query(AgentConfig)
                .filter(AgentConfig.id == agent_id)
                .first()
            )

            if not agent:
                return f"Error: Agent with ID {agent_id} not found"

            return json.dumps(agent.to_dict(), indent=2)
    except Exception as e:
        return f"Error retrieving agent: {str(e)}"


@tool(
    name="list_agent_templates",
    category=ToolCategory.SYSTEM,
    description=(
        "List all available agent templates with descriptions "
        "and recommended tools"
    ),
    requires_api=False,
)
def list_agent_templates() -> str:
    """List all available agent templates.

    This tool displays all available agent templates with their descriptions,
    recommended tools, and system prompts. Templates provide pre-configured
    starting points for creating specialized agents.


    Examples:
        >>> # List all templates
        >>> list_agent_templates()
        "Available agent templates:\\n\\ncoding:\\n  Description: Programming and code assistance\\n  Tools: execute_python, search_web, rag_search\\n  System Prompt: You are an expert programmer who helps write clean, efficient code...\\n\\nresearch:\\n  Description: Research and information gathering\\n  Tools: search_web, scrape_website, rag_search, save_to_knowledge_base\\n  System Prompt: You are a research assistant who helps find and organize information..."

    Note:
        - Templates include: coding, research, creative, calendar
        - Each template has pre-configured tools and prompts
        - Templates can be customized when creating agents
        - System prompts are truncated to 100 characters
    """
    try:
        templates = list_templates()

        if not templates:
            return "No templates available"

        lines = ["Available agent templates:"]
        for tmpl in templates:
            lines.append(f"\n{tmpl.name}:")
            lines.append(f"  Description: {tmpl.description}")
            lines.append(f"  Tools: {', '.join(tmpl.tools)}")
            lines.append(f"  System Prompt: {tmpl.system_prompt[:100]}...")

        return "\n".join(lines)
    except Exception as e:
        return f"Error listing templates: {str(e)}"
