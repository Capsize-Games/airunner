"""Agent tools module.

DEPRECATED: Agent tools have been migrated to the new ToolRegistry system.
Use airunner.components.llm.tools.agent_tools instead.

The old AGENT_TOOLS list has been removed. Agent tools are now available via:
- create_agent
- configure_agent
- list_agents
- delete_agent
- get_agent
- list_agent_templates

All registered automatically via @tool decorator.
"""

__all__ = []
