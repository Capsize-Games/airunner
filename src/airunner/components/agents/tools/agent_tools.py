"""LangChain tools for custom agent management."""

import json
from typing import Optional, List
from langchain_core.tools import BaseTool
from pydantic import BaseModel as PydanticBaseModel, Field
from airunner.components.agents.data.agent_config import AgentConfig
from airunner.components.agents.templates import (
    get_template,
    list_templates,
    template_exists,
)
from airunner.components.data.session_manager import session_scope


class CreateAgentInput(PydanticBaseModel):
    """Input schema for create_agent tool."""

    name: str = Field(description="Unique agent name identifier")
    description: Optional[str] = Field(
        default=None, description="Description of agent purpose"
    )
    system_prompt: str = Field(
        description="Custom system prompt for the agent"
    )
    tools: Optional[List[str]] = Field(
        default=None,
        description="List of tool names available to agent",
    )
    template: str = Field(
        default="custom",
        description=(
            "Template category: coding, research, creative, "
            "calendar, or custom"
        ),
    )


class CreateAgentTool(BaseTool):
    """Tool for creating custom AI agents."""

    name: str = "create_agent"
    description: str = (
        "Create a new custom AI agent with specified name, system prompt, "
        "and available tools. Optionally use a template (coding, research, "
        "creative, calendar) to pre-configure the agent."
    )
    args_schema: type[PydanticBaseModel] = CreateAgentInput

    def _run(
        self,
        name: str,
        system_prompt: str,
        description: Optional[str] = None,
        tools: Optional[List[str]] = None,
        template: str = "custom",
    ) -> str:
        """Create a custom agent.

        Args:
            name: Agent name
            system_prompt: System prompt for agent
            description: Agent description
            tools: List of tool names
            template: Template to use

        Returns:
            Success message with agent ID
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


class ConfigureAgentInput(PydanticBaseModel):
    """Input schema for configure_agent tool."""

    agent_id: int = Field(description="ID of agent to modify")
    name: Optional[str] = Field(default=None, description="New agent name")
    description: Optional[str] = Field(
        default=None, description="New description"
    )
    system_prompt: Optional[str] = Field(
        default=None, description="New system prompt"
    )
    tools: Optional[List[str]] = Field(
        default=None, description="New tool list"
    )


class ConfigureAgentTool(BaseTool):
    """Tool for modifying existing agent configuration."""

    name: str = "configure_agent"
    description: str = (
        "Modify an existing agent's configuration including name, "
        "description, system prompt, or available tools."
    )
    args_schema: type[PydanticBaseModel] = ConfigureAgentInput

    def _run(
        self,
        agent_id: int,
        name: Optional[str] = None,
        description: Optional[str] = None,
        system_prompt: Optional[str] = None,
        tools: Optional[List[str]] = None,
    ) -> str:
        """Configure an existing agent.

        Args:
            agent_id: Agent ID to modify
            name: New name (optional)
            description: New description (optional)
            system_prompt: New system prompt (optional)
            tools: New tool list (optional)

        Returns:
            Success message
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


class ListAgentsInput(PydanticBaseModel):
    """Input schema for list_agents tool."""

    active_only: bool = Field(
        default=True, description="Only show active agents"
    )
    template: Optional[str] = Field(
        default=None, description="Filter by template type"
    )


class ListAgentsTool(BaseTool):
    """Tool for listing all available agents."""

    name: str = "list_agents"
    description: str = (
        "List all available custom agents with their IDs, names, "
        "descriptions, and tool counts."
    )
    args_schema: type[PydanticBaseModel] = ListAgentsInput

    def _run(
        self, active_only: bool = True, template: Optional[str] = None
    ) -> str:
        """List all agents.

        Args:
            active_only: Only show active agents
            template: Filter by template type

        Returns:
            Formatted list of agents
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


class DeleteAgentInput(PydanticBaseModel):
    """Input schema for delete_agent tool."""

    agent_id: int = Field(description="ID of agent to delete")


class DeleteAgentTool(BaseTool):
    """Tool for deleting an agent."""

    name: str = "delete_agent"
    description: str = "Delete a custom agent by ID"
    args_schema: type[PydanticBaseModel] = DeleteAgentInput

    def _run(self, agent_id: int) -> str:
        """Delete an agent.

        Args:
            agent_id: Agent ID to delete

        Returns:
            Success message
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


class GetAgentInput(PydanticBaseModel):
    """Input schema for get_agent tool."""

    agent_id: int = Field(description="ID of agent to retrieve")


class GetAgentTool(BaseTool):
    """Tool for retrieving detailed agent configuration."""

    name: str = "get_agent"
    description: str = "Get detailed configuration for a specific agent by ID"
    args_schema: type[PydanticBaseModel] = GetAgentInput

    def _run(self, agent_id: int) -> str:
        """Get agent details.

        Args:
            agent_id: Agent ID

        Returns:
            JSON formatted agent configuration
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


class ListTemplatesInput(PydanticBaseModel):
    """Input schema for list_templates tool."""

    pass


class ListTemplatesTool(BaseTool):
    """Tool for listing available agent templates."""

    name: str = "list_agent_templates"
    description: str = (
        "List all available agent templates with descriptions "
        "and recommended tools"
    )
    args_schema: type[PydanticBaseModel] = ListTemplatesInput

    def _run(self) -> str:
        """List all agent templates.

        Returns:
            Formatted list of templates
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


# Export all tools
AGENT_TOOLS = [
    CreateAgentTool(),
    ConfigureAgentTool(),
    ListAgentsTool(),
    DeleteAgentTool(),
    GetAgentTool(),
    ListTemplatesTool(),
]
