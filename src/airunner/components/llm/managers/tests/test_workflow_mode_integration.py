"""
Integration tests for mode-based routing in WorkflowManager.
"""

from unittest.mock import Mock

from airunner.components.llm.managers.workflow_manager import (
    WorkflowManager,
)


class TestModeBasedRouting:
    """Test WorkflowManager with mode-based routing enabled."""

    def test_standard_workflow_initialization(self):
        """Test that standard workflow (no mode routing) still works."""
        mock_model = Mock()
        mock_model.bind_tools = Mock(return_value=mock_model)

        manager = WorkflowManager(
            system_prompt="Test prompt",
            chat_model=mock_model,
            tools=None,
            use_mode_routing=False,
        )

        assert manager._use_mode_routing is False
        assert manager._compiled_workflow is not None

    def test_mode_routing_initialization(self):
        """Test that mode-based routing workflow initializes."""
        mock_model = Mock()
        mock_model.bind_tools = Mock(return_value=mock_model)

        manager = WorkflowManager(
            system_prompt="Test prompt",
            chat_model=mock_model,
            tools=None,
            use_mode_routing=True,
        )

        assert manager._use_mode_routing is True
        assert manager._compiled_workflow is not None

    def test_mode_override_parameter(self):
        """Test that mode_override parameter is stored."""
        mock_model = Mock()
        mock_model.bind_tools = Mock(return_value=mock_model)

        manager = WorkflowManager(
            system_prompt="Test prompt",
            chat_model=mock_model,
            tools=None,
            use_mode_routing=True,
            mode_override="code",
        )

        assert manager._mode_override == "code"

    def test_backward_compatibility(self):
        """Test that existing code without mode routing still works."""
        mock_model = Mock()
        mock_model.bind_tools = Mock(return_value=mock_model)

        # Old-style initialization (no mode routing params)
        manager = WorkflowManager(
            system_prompt="Test prompt",
            chat_model=mock_model,
            tools=None,
        )

        # Should default to standard workflow
        assert manager._use_mode_routing is False
        assert manager._compiled_workflow is not None
