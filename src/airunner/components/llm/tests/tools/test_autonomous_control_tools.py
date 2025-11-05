"""Tests for AutonomousControlTools mixin."""

import unittest
from unittest.mock import Mock, MagicMock, patch
import json

from airunner.components.llm.managers.tools.autonomous_control_tools import (
    AutonomousControlTools,
)
from airunner.components.llm.tests.base_test_case import BaseTestCase
from airunner.enums import SignalCode


class MockAutonomousControlToolsClass(AutonomousControlTools):
    """Mock class for testing AutonomousControlTools mixin."""

    def __init__(self):
        self.logger = Mock()
        self.emit_signal = Mock()
        self.rag_manager = None


class TestAutonomousControlTools(BaseTestCase):
    """Test AutonomousControlTools mixin methods."""

    target_class = MockAutonomousControlToolsClass
    public_methods = [
        "get_application_state_tool",
        "schedule_task_tool",
        "propose_action_tool",
        "request_user_input_tool",
        "log_agent_decision_tool",
        "analyze_user_behavior_tool",
        "monitor_system_health_tool",
    ]

    def setUp(self):
        """Set up test with mock autonomous control tools instance."""
        super().setUp()
        self.tools = self.obj  # Alias for backwards compatibility

    def test_get_application_state_tool_creation(self):
        """Test that get_application_state_tool creates a callable tool."""
        tool = self.tools.get_application_state_tool()
        self.assertIsNotNone(tool)
        self.assertEqual(tool.name, "get_application_state")

    def test_get_application_state_returns_json(self):
        """Test that get_application_state returns valid JSON."""
        tool = self.tools.get_application_state_tool()
        result = self.invoke_tool(tool)

        # Should be valid JSON string
        state = json.loads(result)
        self.assertIsInstance(state, dict)
        self.assertIn("application", state)
        self.assertIn("llm", state)

    def test_schedule_task_tool_creation(self):
        """Test that schedule_task_tool creates a callable tool."""
        tool = self.tools.schedule_task_tool()
        self.assertIsNotNone(tool)
        self.assertEqual(tool.name, "schedule_task")

    def test_schedule_task_immediate(self):
        """Test scheduling an immediate task."""
        tool = self.tools.schedule_task_tool()
        result = self.invoke_tool(
            tool,
            task_name="test_task",
            description="Test task description",
            when="now",
        )

        self.assertIn("Scheduled task", result)
        self.assertIn("test_task", result)

        # Verify signal was emitted
        self.tools.emit_signal.assert_called_with(
            SignalCode.SCHEDULE_TASK_SIGNAL,
            {
                "task_name": "test_task",
                "description": "Test task description",
                "when": "now",
                "params": None,
            },
        )

    def test_schedule_task_with_params(self):
        """Test scheduling task with parameters."""
        tool = self.tools.schedule_task_tool()
        params = {"image_prompt": "a cat", "steps": 30}
        result = self.invoke_tool(
            tool,
            task_name="generate_image",
            description="Generate cat image",
            when="in 5 minutes",
            params=params,
        )

        self.assertIn("Scheduled task", result)

        # Verify signal includes params
        call_args = self.tools.emit_signal.call_args
        self.assertEqual(call_args[0][0], SignalCode.SCHEDULE_TASK_SIGNAL)
        self.assertEqual(call_args[0][1]["params"], params)

    def test_set_application_mode_tool_creation(self):
        """Test that set_application_mode_tool creates a callable tool."""
        tool = self.tools.set_application_mode_tool()
        self.assertIsNotNone(tool)
        self.assertEqual(tool.name, "set_application_mode")

    def test_set_application_mode_autonomous(self):
        """Test setting application to autonomous mode."""
        tool = self.tools.set_application_mode_tool()
        result = self.invoke_tool(
            tool, mode="autonomous", reason="Testing autonomous mode"
        )

        self.assertIn("Set application mode", result)
        self.assertIn("autonomous", result)

        # Verify signal was emitted
        self.tools.emit_signal.assert_called_with(
            SignalCode.SET_APPLICATION_MODE_SIGNAL,
            {"mode": "autonomous", "reason": "Testing autonomous mode"},
        )

    def test_set_application_mode_validation(self):
        """Test that invalid modes are rejected."""
        tool = self.tools.set_application_mode_tool()
        result = self.invoke_tool(tool, mode="invalid_mode", reason="Test")

        self.assertIn("must be one of", result.lower())

    def test_request_user_input_tool_creation(self):
        """Test that request_user_input_tool creates a callable tool."""
        tool = self.tools.request_user_input_tool()
        self.assertIsNotNone(tool)
        self.assertEqual(tool.name, "request_user_input")

    def test_request_user_input_approval(self):
        """Test requesting user approval."""
        tool = self.tools.request_user_input_tool()
        result = self.invoke_tool(
            tool,
            prompt="Delete old files?",
            input_type="approval",
            context={"file_count": 42},
        )

        self.assertIn("Requested user input", result)

        # Verify signal was emitted
        self.tools.emit_signal.assert_called()
        call_args = self.tools.emit_signal.call_args
        self.assertEqual(call_args[0][0], SignalCode.REQUEST_USER_INPUT_SIGNAL)
        self.assertIn("prompt", call_args[0][1])

    def test_analyze_user_behavior_tool_creation(self):
        """Test that analyze_user_behavior_tool creates a callable tool."""
        tool = self.tools.analyze_user_behavior_tool()
        self.assertIsNotNone(tool)
        self.assertEqual(tool.name, "analyze_user_behavior")

    def test_propose_action_tool_creation(self):
        """Test that propose_action_tool creates a callable tool."""
        tool = self.tools.propose_action_tool()
        self.assertIsNotNone(tool)
        self.assertEqual(tool.name, "propose_action")

    def test_propose_action_with_rationale(self):
        """Test proposing an action with rationale."""
        tool = self.tools.propose_action_tool()
        result = self.invoke_tool(
            tool,
            action="cleanup_cache",
            rationale="Cache is taking up 5GB of disk space",
            confidence=0.85,
            requires_approval=True,
        )

        self.assertIn("Proposed action", result)
        self.assertIn("cleanup_cache", result)

        # Verify signal was emitted
        self.tools.emit_signal.assert_called_with(
            SignalCode.AGENT_ACTION_PROPOSAL_SIGNAL,
            {
                "action": "cleanup_cache",
                "rationale": "Cache is taking up 5GB of disk space",
                "confidence": 0.85,
                "requires_approval": True,
            },
        )

    @patch("psutil.cpu_percent", return_value=45.0)
    @patch("psutil.virtual_memory")
    @patch("psutil.disk_usage")
    def test_monitor_system_health_tool_creation(
        self, mock_disk, mock_mem, mock_cpu
    ):
        """Test that monitor_system_health_tool creates a callable tool."""
        # Mock memory
        mock_mem.return_value = MagicMock(percent=60.0)
        # Mock disk
        mock_disk.return_value = MagicMock(percent=70.0)

        tool = self.tools.monitor_system_health_tool()
        self.assertIsNotNone(tool)
        self.assertEqual(tool.name, "monitor_system_health")

    @patch("psutil.cpu_percent", return_value=45.0)
    @patch("psutil.virtual_memory")
    @patch("psutil.disk_usage")
    def test_monitor_system_health_returns_metrics(
        self, mock_disk, mock_mem, mock_cpu
    ):
        """Test that monitor_system_health returns valid metrics."""
        # Mock memory
        mock_mem.return_value = MagicMock(percent=60.0)
        # Mock disk
        mock_disk.return_value = MagicMock(percent=70.0)

        tool = self.tools.monitor_system_health_tool()
        result = self.invoke_tool(tool)

        self.assertIn("CPU usage", result)
        self.assertIn("45.0%", result)
        self.assertIn("Memory usage", result)
        self.assertIn("60.0%", result)

    def test_log_agent_decision_tool_creation(self):
        """Test that log_agent_decision_tool creates a callable tool."""
        tool = self.tools.log_agent_decision_tool()
        self.assertIsNotNone(tool)
        self.assertEqual(tool.name, "log_agent_decision")

    def test_log_agent_decision_with_context(self):
        """Test logging agent decision with context."""
        tool = self.tools.log_agent_decision_tool()
        context = {"user_request": "summarize document", "token_count": 5000}
        result = self.invoke_tool(
            tool,
            decision="split_into_chunks",
            reasoning="Document too large for single pass",
            context=context,
        )

        self.assertIn("Logged agent decision", result)
        self.assertIn("split_into_chunks", result)


if __name__ == "__main__":
    unittest.main()
