"""Unit tests for agent_tools module.

Tests all agent management tools with mocked database operations
to ensure proper functionality without database dependencies.
"""

import json
from unittest.mock import Mock, patch, MagicMock

from airunner.components.llm.tools.agent_tools import (
    create_agent,
    configure_agent,
    list_agents,
    delete_agent,
    get_agent,
    list_agent_templates,
)


class TestCreateAgent:
    """Test cases for create_agent tool."""

    @patch("airunner.components.llm.tools.agent_tools.AgentConfig")
    @patch("airunner.components.llm.tools.agent_tools.session_scope")
    @patch("airunner.components.llm.tools.agent_tools.template_exists")
    @patch("airunner.components.llm.tools.agent_tools.get_template")
    def test_create_agent_success_custom(
        self,
        mock_get_template,
        mock_template_exists,
        mock_session_scope,
        mock_agent_config,
    ):
        """Test successfully creating a custom agent."""
        # Arrange
        mock_template_exists.return_value = True
        mock_session = MagicMock()
        mock_session_scope.return_value.__enter__.return_value = mock_session
        mock_session.query.return_value.filter.return_value.first.return_value = (
            None
        )

        # Mock the agent that gets created
        mock_agent = Mock()
        mock_agent.id = 1
        mock_agent.tool_list = []
        mock_agent_config.return_value = mock_agent

        def flush_side_effect():
            # Simulate flush setting the ID
            pass

        mock_session.flush.side_effect = flush_side_effect

        # Act
        result = create_agent(
            name="test_agent",
            system_prompt="You are a test agent.",
            description="Test description",
            tools=["search_web", "scrape_website"],
            template="custom",
        )

        # Assert
        assert "Created agent 'test_agent'" in result
        assert "(ID: 1)" in result
        assert "custom" in result
        assert "2 tools" in result
        mock_session.add.assert_called_once()
        mock_session.flush.assert_called_once()

    @patch("airunner.components.llm.tools.agent_tools.session_scope")
    @patch("airunner.components.llm.tools.agent_tools.template_exists")
    @patch("airunner.components.llm.tools.agent_tools.get_template")
    @patch("airunner.components.llm.tools.agent_tools.list_templates")
    def test_create_agent_invalid_template(
        self,
        mock_list_templates,
        mock_get_template,
        mock_template_exists,
        mock_session_scope,
    ):
        """Test creating agent with invalid template."""
        # Arrange
        mock_template_exists.return_value = False
        mock_template = Mock()
        mock_template.name = "coding"
        mock_list_templates.return_value = [mock_template]

        # Act
        result = create_agent(
            name="test_agent",
            system_prompt="Test",
            template="invalid_template",
        )

        # Assert
        assert "Error: Template 'invalid_template' not found" in result
        assert "coding" in result

    @patch("airunner.components.llm.tools.agent_tools.session_scope")
    @patch("airunner.components.llm.tools.agent_tools.template_exists")
    def test_create_agent_duplicate_name(
        self, mock_template_exists, mock_session_scope
    ):
        """Test creating agent with existing name."""
        # Arrange
        mock_template_exists.return_value = True
        mock_session = MagicMock()
        mock_session_scope.return_value.__enter__.return_value = mock_session

        existing_agent = Mock()
        existing_agent.id = 99
        mock_session.query.return_value.filter.return_value.first.return_value = (
            existing_agent
        )

        # Act
        result = create_agent(
            name="duplicate_agent", system_prompt="Test", template="custom"
        )

        # Assert
        assert (
            "Error: Agent with name 'duplicate_agent' already exists" in result
        )
        assert "(ID: 99)" in result
        mock_session.add.assert_not_called()

    @patch("airunner.components.llm.tools.agent_tools.AgentConfig")
    @patch("airunner.components.llm.tools.agent_tools.session_scope")
    @patch("airunner.components.llm.tools.agent_tools.template_exists")
    @patch("airunner.components.llm.tools.agent_tools.get_template")
    def test_create_agent_with_template_defaults(
        self,
        mock_get_template,
        mock_template_exists,
        mock_session_scope,
        mock_agent_config,
    ):
        """Test creating agent using template defaults."""
        # Arrange
        mock_template_exists.return_value = True
        mock_template = Mock()
        mock_template.system_prompt = "You are a coding expert."
        mock_template.tools = ["execute_python", "search_web"]
        mock_template.description = "Coding assistant"
        mock_get_template.return_value = mock_template

        mock_session = MagicMock()
        mock_session_scope.return_value.__enter__.return_value = mock_session
        mock_session.query.return_value.filter.return_value.first.return_value = (
            None
        )

        mock_agent = Mock()
        mock_agent.id = 2
        mock_agent.tool_list = []
        mock_agent_config.return_value = mock_agent

        # Act - provide empty system_prompt to use template default
        result = create_agent(
            name="coding_agent", system_prompt="", template="coding"
        )

        # Assert
        assert "Created agent 'coding_agent'" in result
        assert "(ID: 2)" in result
        assert "coding" in result
        mock_session.add.assert_called_once()

    @patch("airunner.components.llm.tools.agent_tools.AgentConfig")
    @patch("airunner.components.llm.tools.agent_tools.session_scope")
    @patch("airunner.components.llm.tools.agent_tools.template_exists")
    def test_create_agent_no_tools(
        self, mock_template_exists, mock_session_scope, mock_agent_config
    ):
        """Test creating agent with no tools."""
        # Arrange
        mock_template_exists.return_value = True
        mock_session = MagicMock()
        mock_session_scope.return_value.__enter__.return_value = mock_session
        mock_session.query.return_value.filter.return_value.first.return_value = (
            None
        )

        mock_agent = Mock()
        mock_agent.id = 3
        mock_agent.tool_list = []
        mock_agent_config.return_value = mock_agent

        # Act
        result = create_agent(
            name="no_tools_agent",
            system_prompt="Test",
            template="custom",
            tools=None,
        )

        # Assert
        assert "Created agent 'no_tools_agent'" in result
        assert "0 tools" in result

    @patch("airunner.components.llm.tools.agent_tools.session_scope")
    @patch("airunner.components.llm.tools.agent_tools.template_exists")
    def test_create_agent_error_handling(
        self, mock_template_exists, mock_session_scope
    ):
        """Test error handling during agent creation."""
        # Arrange
        mock_template_exists.return_value = True
        mock_session_scope.side_effect = Exception("Database error")

        # Act
        result = create_agent(
            name="error_agent", system_prompt="Test", template="custom"
        )

        # Assert
        assert "Error creating agent: Database error" in result


class TestConfigureAgent:
    """Test cases for configure_agent tool."""

    @patch("airunner.components.llm.tools.agent_tools.session_scope")
    def test_configure_agent_update_name(self, mock_session_scope):
        """Test updating agent name."""
        # Arrange
        mock_session = MagicMock()
        mock_session_scope.return_value.__enter__.return_value = mock_session

        mock_agent = Mock()
        mock_agent.id = 1
        mock_agent.name = "old_name"
        mock_session.query.return_value.filter.return_value.first.side_effect = [
            mock_agent,  # First call: find agent to update
            None,  # Second call: check new name doesn't exist
        ]

        # Act
        result = configure_agent(agent_id=1, name="new_name")

        # Assert
        assert "Updated agent 'new_name'" in result
        assert "name='new_name'" in result
        assert mock_agent.name == "new_name"
        mock_session.flush.assert_called_once()

    @patch("airunner.components.llm.tools.agent_tools.session_scope")
    def test_configure_agent_not_found(self, mock_session_scope):
        """Test configuring non-existent agent."""
        # Arrange
        mock_session = MagicMock()
        mock_session_scope.return_value.__enter__.return_value = mock_session
        mock_session.query.return_value.filter.return_value.first.return_value = (
            None
        )

        # Act
        result = configure_agent(agent_id=999, name="new_name")

        # Assert
        assert "Error: Agent with ID 999 not found" in result
        mock_session.flush.assert_not_called()

    @patch("airunner.components.llm.tools.agent_tools.session_scope")
    def test_configure_agent_duplicate_name(self, mock_session_scope):
        """Test updating to existing agent name."""
        # Arrange
        mock_session = MagicMock()
        mock_session_scope.return_value.__enter__.return_value = mock_session

        mock_agent = Mock()
        mock_agent.id = 1
        mock_agent.name = "agent1"

        existing_agent = Mock()
        existing_agent.id = 2

        mock_session.query.return_value.filter.return_value.first.side_effect = [
            mock_agent,  # First call: find agent to update
            existing_agent,  # Second call: name already exists
        ]

        # Act
        result = configure_agent(agent_id=1, name="agent2")

        # Assert
        assert "Error: Agent with name 'agent2' already exists" in result
        assert "(ID: 2)" in result
        mock_session.flush.assert_not_called()

    @patch("airunner.components.llm.tools.agent_tools.session_scope")
    def test_configure_agent_multiple_fields(self, mock_session_scope):
        """Test updating multiple agent fields."""
        # Arrange
        mock_session = MagicMock()
        mock_session_scope.return_value.__enter__.return_value = mock_session

        mock_agent = Mock()
        mock_agent.id = 1
        mock_agent.name = "agent1"
        mock_session.query.return_value.filter.return_value.first.return_value = (
            mock_agent
        )

        # Act
        result = configure_agent(
            agent_id=1,
            description="New description",
            system_prompt="New prompt",
            tools=["tool1", "tool2", "tool3"],
        )

        # Assert
        assert "Updated agent 'agent1'" in result
        assert "description" in result
        assert "system_prompt" in result
        assert "tools (3 items)" in result
        assert mock_agent.description == "New description"
        assert mock_agent.system_prompt == "New prompt"
        assert mock_agent.tool_list == ["tool1", "tool2", "tool3"]
        mock_session.flush.assert_called_once()

    @patch("airunner.components.llm.tools.agent_tools.session_scope")
    def test_configure_agent_no_changes(self, mock_session_scope):
        """Test configuring agent with no changes."""
        # Arrange
        mock_session = MagicMock()
        mock_session_scope.return_value.__enter__.return_value = mock_session

        mock_agent = Mock()
        mock_agent.id = 1
        mock_agent.name = "agent1"
        mock_session.query.return_value.filter.return_value.first.return_value = (
            mock_agent
        )

        # Act - no parameters provided
        result = configure_agent(agent_id=1)

        # Assert
        assert "No changes made to agent 'agent1'" in result
        mock_session.flush.assert_called_once()

    @patch("airunner.components.llm.tools.agent_tools.session_scope")
    def test_configure_agent_error_handling(self, mock_session_scope):
        """Test error handling during configuration."""
        # Arrange
        mock_session_scope.side_effect = Exception("Database error")

        # Act
        result = configure_agent(agent_id=1, name="new_name")

        # Assert
        assert "Error configuring agent: Database error" in result


class TestListAgents:
    """Test cases for list_agents tool."""

    @patch("airunner.components.llm.tools.agent_tools.session_scope")
    def test_list_agents_success(self, mock_session_scope):
        """Test successfully listing agents."""
        # Arrange
        mock_session = MagicMock()
        mock_session_scope.return_value.__enter__.return_value = mock_session

        mock_agent1 = Mock()
        mock_agent1.id = 1
        mock_agent1.name = "agent1"
        mock_agent1.is_active = True
        mock_agent1.template = "coding"
        mock_agent1.tool_list = ["tool1", "tool2"]
        mock_agent1.description = "First agent"

        mock_agent2 = Mock()
        mock_agent2.id = 2
        mock_agent2.name = "agent2"
        mock_agent2.is_active = True
        mock_agent2.template = "research"
        mock_agent2.tool_list = ["tool1"]
        mock_agent2.description = None

        mock_query = mock_session.query.return_value
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value.all.return_value = [
            mock_agent1,
            mock_agent2,
        ]

        # Act
        result = list_agents()

        # Assert
        assert "Available agents:" in result
        assert "[1] agent1 (active) - coding template - 2 tools" in result
        assert "First agent" in result
        assert "[2] agent2 (active) - research template - 1 tools" in result

    @patch("airunner.components.llm.tools.agent_tools.session_scope")
    def test_list_agents_no_agents(self, mock_session_scope):
        """Test listing when no agents exist."""
        # Arrange
        mock_session = MagicMock()
        mock_session_scope.return_value.__enter__.return_value = mock_session

        mock_query = mock_session.query.return_value
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value.all.return_value = []

        # Act
        result = list_agents()

        # Assert
        assert result == "No agents found"

    @patch("airunner.components.llm.tools.agent_tools.session_scope")
    def test_list_agents_include_inactive(self, mock_session_scope):
        """Test listing including inactive agents."""
        # Arrange
        mock_session = MagicMock()
        mock_session_scope.return_value.__enter__.return_value = mock_session

        mock_agent = Mock()
        mock_agent.id = 1
        mock_agent.name = "inactive_agent"
        mock_agent.is_active = False
        mock_agent.template = "custom"
        mock_agent.tool_list = []
        mock_agent.description = None

        mock_query = mock_session.query.return_value
        # When active_only=False, filter should not be called for is_active
        mock_query.order_by.return_value.all.return_value = [mock_agent]

        # Act
        result = list_agents(active_only=False)

        # Assert
        assert "[1] inactive_agent (inactive)" in result

    @patch("airunner.components.llm.tools.agent_tools.session_scope")
    def test_list_agents_filter_by_template(self, mock_session_scope):
        """Test listing agents filtered by template."""
        # Arrange
        mock_session = MagicMock()
        mock_session_scope.return_value.__enter__.return_value = mock_session

        mock_agent = Mock()
        mock_agent.id = 1
        mock_agent.name = "coding_agent"
        mock_agent.is_active = True
        mock_agent.template = "coding"
        mock_agent.tool_list = ["tool1"]
        mock_agent.description = None

        mock_query = mock_session.query.return_value
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value.all.return_value = [mock_agent]

        # Act
        result = list_agents(template="coding")

        # Assert
        assert "[1] coding_agent (active) - coding template" in result
        # Verify filter was called with template
        assert mock_query.filter.call_count >= 1

    @patch("airunner.components.llm.tools.agent_tools.session_scope")
    def test_list_agents_error_handling(self, mock_session_scope):
        """Test error handling during listing."""
        # Arrange
        mock_session_scope.side_effect = Exception("Database error")

        # Act
        result = list_agents()

        # Assert
        assert "Error listing agents: Database error" in result


class TestDeleteAgent:
    """Test cases for delete_agent tool."""

    @patch("airunner.components.llm.tools.agent_tools.session_scope")
    def test_delete_agent_success(self, mock_session_scope):
        """Test successfully deleting an agent."""
        # Arrange
        mock_session = MagicMock()
        mock_session_scope.return_value.__enter__.return_value = mock_session

        mock_agent = Mock()
        mock_agent.id = 1
        mock_agent.name = "agent_to_delete"
        mock_session.query.return_value.filter.return_value.first.return_value = (
            mock_agent
        )

        # Act
        result = delete_agent(agent_id=1)

        # Assert
        assert "Deleted agent 'agent_to_delete' (ID: 1)" in result
        mock_session.delete.assert_called_once_with(mock_agent)
        mock_session.flush.assert_called_once()

    @patch("airunner.components.llm.tools.agent_tools.session_scope")
    def test_delete_agent_not_found(self, mock_session_scope):
        """Test deleting non-existent agent."""
        # Arrange
        mock_session = MagicMock()
        mock_session_scope.return_value.__enter__.return_value = mock_session
        mock_session.query.return_value.filter.return_value.first.return_value = (
            None
        )

        # Act
        result = delete_agent(agent_id=999)

        # Assert
        assert "Error: Agent with ID 999 not found" in result
        mock_session.delete.assert_not_called()
        mock_session.flush.assert_not_called()

    @patch("airunner.components.llm.tools.agent_tools.session_scope")
    def test_delete_agent_error_handling(self, mock_session_scope):
        """Test error handling during deletion."""
        # Arrange
        mock_session_scope.side_effect = Exception("Database error")

        # Act
        result = delete_agent(agent_id=1)

        # Assert
        assert "Error deleting agent: Database error" in result


class TestGetAgent:
    """Test cases for get_agent tool."""

    @patch("airunner.components.llm.tools.agent_tools.session_scope")
    def test_get_agent_success(self, mock_session_scope):
        """Test successfully retrieving agent details."""
        # Arrange
        mock_session = MagicMock()
        mock_session_scope.return_value.__enter__.return_value = mock_session

        mock_agent = Mock()
        mock_agent.id = 1
        mock_agent.name = "test_agent"
        mock_agent.to_dict.return_value = {
            "id": 1,
            "name": "test_agent",
            "description": "Test description",
            "system_prompt": "You are a test agent",
            "template": "custom",
            "tools": ["tool1", "tool2"],
            "is_active": True,
        }
        mock_session.query.return_value.filter.return_value.first.return_value = (
            mock_agent
        )

        # Act
        result = get_agent(agent_id=1)

        # Assert
        result_dict = json.loads(result)
        assert result_dict["id"] == 1
        assert result_dict["name"] == "test_agent"
        assert result_dict["description"] == "Test description"
        mock_agent.to_dict.assert_called_once()

    @patch("airunner.components.llm.tools.agent_tools.session_scope")
    def test_get_agent_not_found(self, mock_session_scope):
        """Test retrieving non-existent agent."""
        # Arrange
        mock_session = MagicMock()
        mock_session_scope.return_value.__enter__.return_value = mock_session
        mock_session.query.return_value.filter.return_value.first.return_value = (
            None
        )

        # Act
        result = get_agent(agent_id=999)

        # Assert
        assert "Error: Agent with ID 999 not found" in result

    @patch("airunner.components.llm.tools.agent_tools.session_scope")
    def test_get_agent_error_handling(self, mock_session_scope):
        """Test error handling during retrieval."""
        # Arrange
        mock_session_scope.side_effect = Exception("Database error")

        # Act
        result = get_agent(agent_id=1)

        # Assert
        assert "Error retrieving agent: Database error" in result


class TestListAgentTemplates:
    """Test cases for list_agent_templates tool."""

    @patch("airunner.components.llm.tools.agent_tools.list_templates")
    def test_list_agent_templates_success(self, mock_list_templates):
        """Test successfully listing agent templates."""
        # Arrange
        mock_template1 = Mock()
        mock_template1.name = "coding"
        mock_template1.description = "Programming and code assistance"
        mock_template1.tools = ["execute_python", "search_web", "rag_search"]
        mock_template1.system_prompt = (
            "You are an expert programmer who helps write clean, "
            "efficient code with best practices."
        )

        mock_template2 = Mock()
        mock_template2.name = "research"
        mock_template2.description = "Research and information gathering"
        mock_template2.tools = [
            "search_web",
            "scrape_website",
            "rag_search",
            "save_to_knowledge_base",
        ]
        mock_template2.system_prompt = (
            "You are a research assistant who helps find and "
            "organize information effectively."
        )

        mock_list_templates.return_value = [mock_template1, mock_template2]

        # Act
        result = list_agent_templates()

        # Assert
        assert "Available agent templates:" in result
        assert "coding:" in result
        assert "Programming and code assistance" in result
        assert "execute_python, search_web, rag_search" in result
        assert "research:" in result
        assert "Research and information gathering" in result
        assert (
            "search_web, scrape_website, rag_search, save_to_knowledge_base"
            in result
        )

    @patch("airunner.components.llm.tools.agent_tools.list_templates")
    def test_list_agent_templates_no_templates(self, mock_list_templates):
        """Test listing when no templates exist."""
        # Arrange
        mock_list_templates.return_value = []

        # Act
        result = list_agent_templates()

        # Assert
        assert result == "No templates available"

    @patch("airunner.components.llm.tools.agent_tools.list_templates")
    def test_list_agent_templates_truncated_prompt(self, mock_list_templates):
        """Test that system prompts are truncated to 100 characters."""
        # Arrange
        mock_template = Mock()
        mock_template.name = "long_prompt"
        mock_template.description = "Test template"
        mock_template.tools = ["tool1"]
        mock_template.system_prompt = "A" * 150  # 150 character prompt

        mock_list_templates.return_value = [mock_template]

        # Act
        result = list_agent_templates()

        # Assert
        # Should be truncated to 100 chars + "..."
        assert "A" * 100 + "..." in result
        # Should not contain full 150 characters
        assert "A" * 150 not in result

    @patch("airunner.components.llm.tools.agent_tools.list_templates")
    def test_list_agent_templates_error_handling(self, mock_list_templates):
        """Test error handling during template listing."""
        # Arrange
        mock_list_templates.side_effect = Exception("Template error")

        # Act
        result = list_agent_templates()

        # Assert
        assert "Error listing templates: Template error" in result
