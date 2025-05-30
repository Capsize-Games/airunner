"""Unit tests for AnalysisToolsMixin to ensure robust handling of None for update_user_data_engine and update_user_data_tool."""

import unittest
from unittest.mock import MagicMock, patch, PropertyMock
from airunner.handlers.llm.agent.agents.base import BaseAgent
from airunner.handlers.llm.agent.agents.tool_mixins.analysis_tools_mixin import (
    AnalysisToolsMixin,
)


class DummyAgent(BaseAgent, AnalysisToolsMixin):
    pass


class TestAnalysisToolsMixinNoneHandling(unittest.TestCase):
    def setUp(self):
        with patch.object(BaseAgent, "__init__", return_value=None):
            self.agent = DummyAgent()
        # Patch the logger property to return a MagicMock
        logger_patcher = patch.object(
            DummyAgent, "logger", new_callable=PropertyMock
        )
        self.mock_logger = logger_patcher.start()
        self.addCleanup(logger_patcher.stop)
        self.mock_logger.return_value = MagicMock()
        # Patch required internal attributes to avoid AttributeError
        self.agent._use_memory = True
        self.agent._conversation = MagicMock()
        self.agent._conversation.value = True
        self.agent._conversation.formatted_messages = "test context"
        self.agent._extract_analysis = lambda x: "analysis result"
        self.agent._is_meaningless_magicmock = lambda x: False
        self.agent._llm = MagicMock()  # Prevent AttributeError on llm property

    def test_update_user_data_engine_none(self):
        # Simulate property raising AttributeError to trigger fallback
        def raise_attr_error(*args, **kwargs):
            raise AttributeError("update_user_data_engine is None")

        with patch.object(
            self.agent.__class__,
            "update_user_data_engine",
            new_callable=PropertyMock,
        ) as mock_engine:
            mock_engine.side_effect = raise_attr_error
            # Should not raise, should log error and fallback
            with patch.object(
                self.agent, "_fallback_update_user_data", return_value=None
            ) as fallback:
                self.agent._update_user_data()
                fallback.assert_called()

    def test_update_user_data_tool_none(self):
        # Simulate property returning None
        with patch.object(
            DummyAgent, "update_user_data_tool", new_callable=PropertyMock
        ) as mock_tool:
            mock_tool.return_value = None
            result = self.agent._fallback_update_user_data("context")
            self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
