"""Tests for agent configuration widget.

Note: GUI widget tests require pytest-qt plugin which will be set up in issue #1869.
For now, these tests verify basic widget functionality programmatically.
"""

import pytest
from airunner.components.agents.data.agent_config import AgentConfig
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


class TestAgentConfigWidgetImport:
    """Tests for AgentConfigWidget import and basic structure."""

    def test_widget_import(self):
        """Test that widget can be imported."""
        from airunner.components.agents.gui.widgets.agent_config_widget import (
            AgentConfigWidget,
        )

        assert AgentConfigWidget is not None

    def test_widget_has_required_signals(self):
        """Test that widget defines required signals."""
        from airunner.components.agents.gui.widgets.agent_config_widget import (
            AgentConfigWidget,
        )

        assert hasattr(AgentConfigWidget, "agent_created")
        assert hasattr(AgentConfigWidget, "agent_updated")
        assert hasattr(AgentConfigWidget, "agent_deleted")

    def test_widget_has_required_methods(self):
        """Test that widget has all required methods."""
        from airunner.components.agents.gui.widgets.agent_config_widget import (
            AgentConfigWidget,
        )

        required_methods = [
            "setup_ui",
            "load_agents",
            "load_templates",
            "on_agent_selected",
            "on_new_agent",
            "on_template_changed",
            "on_save_agent",
            "on_delete_agent",
            "on_cancel",
            "on_test_agent",
            "clear_form",
        ]

        for method_name in required_methods:
            assert hasattr(AgentConfigWidget, method_name)


# TODO: Full GUI tests will be implemented in #1869
# These tests will use pytest-qt to test:
# - Widget initialization
# - Template combo population
# - Creating new agents
# - Loading existing agents
# - Updating agents
# - Deleting agents
# - Form validation
# - Template autofill
# - Signal emissions
