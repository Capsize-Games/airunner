# Agent Management System

The agents component provides LangChain tools for creating, configuring, and managing custom AI agents with specialized capabilities.

## Overview

Custom agents allow users to create specialized AI assistants with:
- **Custom system prompts** - Define agent behavior and personality
- **Tool sets** - Select which tools the agent can use
- **Templates** - Pre-configured agents for common tasks
- **Persistence** - Agents stored in database for reuse

## Agent Templates

Pre-configured agent templates for common use cases:

- **coding** - Software development assistant with file operations
- **research** - Information gathering and analysis
- **creative** - Content creation and storytelling
- **calendar** - Scheduling and event management
- **custom** - User-defined configuration

## Available Tools

### create_agent
Create a new custom agent with specified configuration.

**Parameters:**
- `name` (str): Unique agent identifier
- `system_prompt` (str): Custom system prompt
- `description` (str, optional): Agent description
- `tools` (list[str], optional): List of tool names
- `template` (str, default="custom"): Template to use

**Example:**
```python
from airunner.components.agents.tools import AGENT_TOOLS

create_tool = AGENT_TOOLS[0]  # CreateAgentTool
result = create_tool._run(
    name="code_helper",
    system_prompt="You are an expert Python developer",
    tools=["read_file", "write_file", "run_command"],
    template="coding"
)
```

### configure_agent
Modify existing agent configuration.

**Parameters:**
- `agent_id` (int): ID of agent to modify
- `name` (str, optional): New name
- `description` (str, optional): New description
- `system_prompt` (str, optional): New system prompt
- `tools` (list[str], optional): New tool list

### list_agents
List all available agents with filtering.

**Parameters:**
- `active_only` (bool, default=True): Only show active agents
- `template` (str, optional): Filter by template type

### delete_agent
Delete an agent by ID.

**Parameters:**
- `agent_id` (int): ID of agent to delete

### get_agent
Retrieve detailed configuration for an agent.

**Parameters:**
- `agent_id` (int): ID of agent to retrieve

**Returns:** JSON formatted agent configuration

### list_agent_templates
List all available agent templates with descriptions.

## Database Schema

### agent_configs table

| Column | Type | Description |
|--------|------|-------------|
| id | Integer | Primary key |
| name | String(255) | Unique agent name |
| description | Text | Agent description |
| system_prompt | Text | System prompt |
| tools | Text | Comma-separated tool names |
| template | String(50) | Template category |
| created_at | DateTime | Creation timestamp |
| updated_at | DateTime | Last modification timestamp |
| is_active | Integer | Active status (1=active, 0=inactive) |

**Indexes:**
- `ix_agent_configs_name` (unique)
- `ix_agent_configs_template`
- `ix_agent_configs_is_active`
- `ix_agent_configs_created_at`

## Usage Example

```python
from airunner.components.agents.tools.agent_tools import (
    CreateAgentTool,
    ListAgentsTool,
    GetAgentTool,
)

# Create a coding agent
create_tool = CreateAgentTool()
result = create_tool._run(
    name="python_expert",
    system_prompt="You are a Python expert who writes clean, tested code",
    tools=["read_file", "write_file", "search_files"],
    template="coding"
)
print(result)  # "Created agent 'python_expert' (ID: 1)..."

# List all agents
list_tool = ListAgentsTool()
agents = list_tool._run()
print(agents)

# Get specific agent details
get_tool = GetAgentTool()
details = get_tool._run(agent_id=1)
print(details)  # JSON formatted config
```

## Integration with LLM

These tools are automatically available to the LLM when registered. The LLM can:
1. Create agents for specific tasks
2. Configure agents based on user needs
3. Switch between agents for different contexts
4. List available agents to understand capabilities

## Testing

Run tests with:
```bash
python -m pytest src/airunner/components/agents/tests/test_agent_tools.py -v
```

Test coverage includes:
- Agent CRUD operations
- Template usage
- Error handling
- Database persistence
- Tool list management

## Files

- `data/agent_config.py` - SQLAlchemy model
- `templates.py` - Agent template definitions
- `tools/agent_tools.py` - LangChain tool implementations
- `tests/test_agent_tools.py` - Comprehensive test suite
