"""Tests for agent management tools."""

import pytest
from airunner.components.agents.data.agent_config import AgentConfig
from airunner.components.agents.tools.agent_tools import (
    CreateAgentTool,
    ConfigureAgentTool,
    ListAgentsTool,
    DeleteAgentTool,
    GetAgentTool,
    ListTemplatesTool,
)
from airunner.components.agents.templates import AGENT_TEMPLATES
from airunner.components.data.session_manager import session_scope


@pytest.fixture
def clean_agents():
    """Clean agent_configs table before and after tests."""
    with session_scope() as session:
        session.query(AgentConfig).delete()
        session.commit()
    yield
    with session_scope() as session:
        session.query(AgentConfig).delete()
        session.commit()


class TestCreateAgentTool:
    """Tests for CreateAgentTool."""

    def test_create_basic_agent(self, clean_agents):
        """Test creating a basic custom agent."""
        tool = CreateAgentTool()
        result = tool._run(
            name="test_agent",
            system_prompt="You are a test assistant",
            description="Test agent for unit testing",
            tools=["read_file", "write_file"],
            template="custom",
        )

        assert "Created agent 'test_agent'" in result
        assert "custom" in result
        assert "2 tools" in result

        # Verify in database
        with session_scope() as session:
            agent = (
                session.query(AgentConfig)
                .filter(AgentConfig.name == "test_agent")
                .first()
            )
            assert agent is not None
            assert agent.description == "Test agent for unit testing"
            assert agent.system_prompt == "You are a test assistant"
            assert set(agent.tool_list) == {"read_file", "write_file"}

    def test_create_from_template(self, clean_agents):
        """Test creating agent from template."""
        tool = CreateAgentTool()
        result = tool._run(
            name="coding_assistant",
            system_prompt="",  # Should use template prompt
            template="coding",
        )

        assert "Created agent 'coding_assistant'" in result
        assert "coding" in result

        # Verify template values used
        with session_scope() as session:
            agent = (
                session.query(AgentConfig)
                .filter(AgentConfig.name == "coding_assistant")
                .first()
            )
            assert agent is not None
            template = AGENT_TEMPLATES["coding"]
            assert agent.system_prompt == template.system_prompt
            assert set(agent.tool_list) == set(template.tools)

    def test_create_duplicate_name_fails(self, clean_agents):
        """Test that creating agent with duplicate name fails."""
        tool = CreateAgentTool()

        # Create first agent
        tool._run(
            name="duplicate",
            system_prompt="First agent",
            template="custom",
        )

        # Try to create second with same name
        result = tool._run(
            name="duplicate",
            system_prompt="Second agent",
            template="custom",
        )

        assert "Error" in result
        assert "already exists" in result

    def test_create_with_invalid_template(self, clean_agents):
        """Test creating agent with invalid template."""
        tool = CreateAgentTool()
        result = tool._run(
            name="test",
            system_prompt="Test",
            template="nonexistent_template",
        )

        assert "Error" in result
        assert "not found" in result


class TestConfigureAgentTool:
    """Tests for ConfigureAgentTool."""

    def test_update_agent_name(self, clean_agents):
        """Test updating agent name."""
        # Create agent
        create_tool = CreateAgentTool()
        create_tool._run(
            name="old_name",
            system_prompt="Test agent",
            template="custom",
        )

        # Get agent ID
        with session_scope() as session:
            agent = (
                session.query(AgentConfig)
                .filter(AgentConfig.name == "old_name")
                .first()
            )
            agent_id = agent.id

        # Update name
        config_tool = ConfigureAgentTool()
        result = config_tool._run(agent_id=agent_id, name="new_name")

        assert "Updated agent 'new_name'" in result
        assert "name='new_name'" in result

        # Verify update
        with session_scope() as session:
            agent = (
                session.query(AgentConfig)
                .filter(AgentConfig.id == agent_id)
                .first()
            )
            assert agent.name == "new_name"

    def test_update_agent_tools(self, clean_agents):
        """Test updating agent tools."""
        # Create agent
        create_tool = CreateAgentTool()
        create_tool._run(
            name="agent",
            system_prompt="Test",
            tools=["tool1"],
            template="custom",
        )

        # Get agent ID
        with session_scope() as session:
            agent = (
                session.query(AgentConfig)
                .filter(AgentConfig.name == "agent")
                .first()
            )
            agent_id = agent.id

        # Update tools
        config_tool = ConfigureAgentTool()
        result = config_tool._run(
            agent_id=agent_id, tools=["tool1", "tool2", "tool3"]
        )

        assert "Updated agent" in result
        assert "3 items" in result

        # Verify update
        with session_scope() as session:
            agent = (
                session.query(AgentConfig)
                .filter(AgentConfig.id == agent_id)
                .first()
            )
            assert set(agent.tool_list) == {"tool1", "tool2", "tool3"}

    def test_update_nonexistent_agent(self, clean_agents):
        """Test updating nonexistent agent."""
        config_tool = ConfigureAgentTool()
        result = config_tool._run(agent_id=99999, name="test")

        assert "Error" in result
        assert "not found" in result

    def test_update_with_duplicate_name(self, clean_agents):
        """Test updating to duplicate name fails."""
        # Create two agents
        create_tool = CreateAgentTool()
        create_tool._run(
            name="agent1", system_prompt="Test 1", template="custom"
        )
        create_tool._run(
            name="agent2", system_prompt="Test 2", template="custom"
        )

        # Get agent2 ID
        with session_scope() as session:
            agent = (
                session.query(AgentConfig)
                .filter(AgentConfig.name == "agent2")
                .first()
            )
            agent_id = agent.id

        # Try to rename agent2 to agent1
        config_tool = ConfigureAgentTool()
        result = config_tool._run(agent_id=agent_id, name="agent1")

        assert "Error" in result
        assert "already exists" in result


class TestListAgentsTool:
    """Tests for ListAgentsTool."""

    def test_list_empty(self, clean_agents):
        """Test listing when no agents exist."""
        tool = ListAgentsTool()
        result = tool._run()

        assert "No agents found" in result

    def test_list_multiple_agents(self, clean_agents):
        """Test listing multiple agents."""
        # Create agents
        create_tool = CreateAgentTool()
        create_tool._run(
            name="agent1",
            system_prompt="Test 1",
            description="First agent",
            template="coding",
        )
        create_tool._run(
            name="agent2",
            system_prompt="Test 2",
            description="Second agent",
            template="research",
        )

        # List agents
        list_tool = ListAgentsTool()
        result = list_tool._run()

        assert "Available agents:" in result
        assert "agent1" in result
        assert "agent2" in result
        assert "coding" in result
        assert "research" in result
        assert "First agent" in result
        assert "Second agent" in result

    def test_list_filter_by_template(self, clean_agents):
        """Test filtering agents by template."""
        # Create agents with different templates
        create_tool = CreateAgentTool()
        create_tool._run(name="coder", system_prompt="Test", template="coding")
        create_tool._run(
            name="researcher", system_prompt="Test", template="research"
        )

        # List only coding agents
        list_tool = ListAgentsTool()
        result = list_tool._run(template="coding")

        assert "coder" in result
        assert "researcher" not in result


class TestDeleteAgentTool:
    """Tests for DeleteAgentTool."""

    def test_delete_agent(self, clean_agents):
        """Test deleting an agent."""
        # Create agent
        create_tool = CreateAgentTool()
        create_tool._run(
            name="to_delete", system_prompt="Test", template="custom"
        )

        # Get agent ID
        with session_scope() as session:
            agent = (
                session.query(AgentConfig)
                .filter(AgentConfig.name == "to_delete")
                .first()
            )
            agent_id = agent.id

        # Delete agent
        delete_tool = DeleteAgentTool()
        result = delete_tool._run(agent_id=agent_id)

        assert "Deleted agent 'to_delete'" in result

        # Verify deletion
        with session_scope() as session:
            agent = (
                session.query(AgentConfig)
                .filter(AgentConfig.id == agent_id)
                .first()
            )
            assert agent is None

    def test_delete_nonexistent_agent(self, clean_agents):
        """Test deleting nonexistent agent."""
        delete_tool = DeleteAgentTool()
        result = delete_tool._run(agent_id=99999)

        assert "Error" in result
        assert "not found" in result


class TestGetAgentTool:
    """Tests for GetAgentTool."""

    def test_get_agent_details(self, clean_agents):
        """Test retrieving agent details."""
        # Create agent
        create_tool = CreateAgentTool()
        create_tool._run(
            name="test_agent",
            system_prompt="Test prompt",
            description="Test description",
            tools=["tool1", "tool2"],
            template="custom",
        )

        # Get agent ID
        with session_scope() as session:
            agent = (
                session.query(AgentConfig)
                .filter(AgentConfig.name == "test_agent")
                .first()
            )
            agent_id = agent.id

        # Get agent details
        get_tool = GetAgentTool()
        result = get_tool._run(agent_id=agent_id)

        # Verify JSON output
        assert '"name": "test_agent"' in result
        assert '"description": "Test description"' in result
        assert '"system_prompt": "Test prompt"' in result
        assert "tool1" in result
        assert "tool2" in result

    def test_get_nonexistent_agent(self, clean_agents):
        """Test getting nonexistent agent."""
        get_tool = GetAgentTool()
        result = get_tool._run(agent_id=99999)

        assert "Error" in result
        assert "not found" in result


class TestListTemplatesTool:
    """Tests for ListTemplatesTool."""

    def test_list_templates(self):
        """Test listing all templates."""
        tool = ListTemplatesTool()
        result = tool._run()

        assert "Available agent templates:" in result
        assert "coding" in result
        assert "research" in result
        assert "creative" in result
        assert "calendar" in result
        assert "custom" in result
