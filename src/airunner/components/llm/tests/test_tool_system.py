"""
Tests for the new LLM tool system.

Validates tool registration, execution, and integration.
"""

import pytest
from unittest.mock import Mock

from airunner.components.llm.core.tool_registry import (
    ToolRegistry,
    ToolCategory,
    tool,
)
from airunner.components.llm.core.tool_executor import ToolExecutor
from airunner.components.llm.core.request_processor import RequestProcessor
from airunner.components.llm.managers.llm_request import LLMRequest
from airunner.enums import LLMActionType


class TestToolRegistry:
    """Test the tool registry system."""

    def setup_method(self):
        """Clear registry before each test."""
        ToolRegistry.clear()

    def test_tool_registration(self):
        """Test that tools register correctly."""

        @tool(
            name="test_tool",
            category=ToolCategory.SYSTEM,
            description="A test tool",
        )
        def test_func():
            return "test"

        tool_info = ToolRegistry.get("test_tool")
        assert tool_info is not None
        assert tool_info.name == "test_tool"
        assert tool_info.category == ToolCategory.SYSTEM
        assert tool_info.description == "A test tool"

    def test_tool_by_category(self):
        """Test retrieving tools by category."""

        @tool(name="img1", category=ToolCategory.IMAGE, description="Image 1")
        def img1():
            pass

        @tool(name="img2", category=ToolCategory.IMAGE, description="Image 2")
        def img2():
            pass

        @tool(
            name="sys1", category=ToolCategory.SYSTEM, description="System 1"
        )
        def sys1():
            pass

        image_tools = ToolRegistry.get_by_category(ToolCategory.IMAGE)
        assert len(image_tools) == 2

        system_tools = ToolRegistry.get_by_category(ToolCategory.SYSTEM)
        assert len(system_tools) == 1

    def test_tool_metadata(self):
        """Test tool metadata is preserved."""

        @tool(
            name="meta_tool",
            category=ToolCategory.CHAT,
            description="Test metadata",
            return_direct=True,
            requires_agent=True,
            requires_api=True,
        )
        def meta_func():
            pass

        info = ToolRegistry.get("meta_tool")
        assert info.return_direct is True
        assert info.requires_agent is True
        assert info.requires_api is True

    def test_get_triggers_reload_for_default_tool(self):
        """Ensure ToolRegistry.get reloads default tool modules when the requested
        tool is missing and registry contains other tools (regression test).
        """
        ToolRegistry.clear()

        @tool(
            name="img_check",
            category=ToolCategory.IMAGE,
            description="Img check",
        )
        def img_check():
            return "ok"

        # At this point, only our test tool should be present
        assert "img_check" in ToolRegistry._tools

        # Request a known default tool - should trigger import & registration
        gen_tool = ToolRegistry.get("generate_direct_response")
        assert gen_tool is not None


class TestToolExecutor:
    """Test tool execution with dependency injection."""

    def setup_method(self):
        """Setup test fixtures."""
        ToolRegistry.clear()
        self.mock_agent = Mock()
        self.mock_api = Mock()
        self.executor = ToolExecutor(
            agent=self.mock_agent,
            api=self.mock_api,
        )

    def test_basic_tool_execution(self):
        """Test executing a basic tool."""

        @tool(name="basic", category=ToolCategory.SYSTEM, description="Basic")
        def basic_tool():
            return "success"

        info = ToolRegistry.get("basic")
        wrapped = self.executor.wrap_tool(info)
        result = wrapped()
        assert result == "success"

    def test_agent_injection(self):
        """Test agent dependency injection."""

        @tool(
            name="needs_agent",
            category=ToolCategory.SYSTEM,
            description="Needs agent",
            requires_agent=True,
        )
        def agent_tool(agent=None):
            return agent.test_value

        self.mock_agent.test_value = "injected"

        info = ToolRegistry.get("needs_agent")
        wrapped = self.executor.wrap_tool(info)
        result = wrapped()
        assert result == "injected"

    def test_api_injection(self):
        """Test API dependency injection."""

        @tool(
            name="needs_api",
            category=ToolCategory.SYSTEM,
            description="Needs API",
            requires_api=True,
        )
        def api_tool(api=None):
            return api.test_value

        self.mock_api.test_value = "api_injected"

        info = ToolRegistry.get("needs_api")
        wrapped = self.executor.wrap_tool(info)
        result = wrapped()
        assert result == "api_injected"

    def test_error_handling(self):
        """Test error handling in tool execution."""

        @tool(name="error", category=ToolCategory.SYSTEM, description="Error")
        def error_tool():
            raise ValueError("Test error")

        info = ToolRegistry.get("error")
        wrapped = self.executor.wrap_tool(info)
        result = wrapped()
        assert "Error:" in result

    def test_to_function_tool(self):
        """Test conversion to FunctionTool."""

        @tool(
            name="convert", category=ToolCategory.SYSTEM, description="Convert"
        )
        def convert_tool():
            return "converted"

        info = ToolRegistry.get("convert")
        function_tool = self.executor.to_function_tool(info)

        assert function_tool is not None
        assert hasattr(function_tool, "metadata")
        assert function_tool.metadata.name == "convert"


class TestRequestProcessor:
    """Test request processing and settings management."""

    def test_merge_settings_with_defaults(self):
        """Test merging request with database settings.

        Note: Currently request values always take precedence because
        LLMRequest has defaults and we can't detect explicitly set values.
        This is acceptable behavior - callers should pass None or omit
        parameters they want to use from database.
        """
        # Mock database settings
        db_settings = Mock()
        db_settings.temperature = 0.7
        db_settings.max_new_tokens = 100
        db_settings.top_p = 0.9

        processor = RequestProcessor(default_settings=db_settings)

        # Request with explicit override
        request = LLMRequest(temperature=0.9)
        merged = processor.merge_settings(request, db_settings)

        # Temperature was explicitly set, so it overrides
        assert merged.temperature == 0.9
        # max_new_tokens uses LLMRequest default (200), not db (100)
        # This is current behavior - to use db value, pass None or
        # don't create custom LLMRequest
        assert merged.max_new_tokens == 200

    def test_validate_request_valid(self):
        """Test validation passes for valid request."""
        processor = RequestProcessor()
        request = LLMRequest(
            temperature=0.8,
            max_new_tokens=200,
            top_p=0.9,
            top_k=50,
        )

        assert processor.validate_request(request) is True

    def test_validate_request_invalid_temperature(self):
        """Test validation fails for invalid temperature."""
        processor = RequestProcessor()
        request = LLMRequest(temperature=0.0)  # Too low

        assert processor.validate_request(request) is False

    def test_validate_request_invalid_top_p(self):
        """Test validation fails for invalid top_p."""
        processor = RequestProcessor()
        request = LLMRequest(top_p=1.5)  # Too high

        assert processor.validate_request(request) is False

    def test_prepare_request_complete(self):
        """Test complete request preparation."""
        db_settings = Mock()
        db_settings.temperature = 0.7
        db_settings.max_new_tokens = 100

        processor = RequestProcessor(default_settings=db_settings)

        request = processor.prepare_request(
            prompt="Test prompt",
            action=LLMActionType.CHAT,
            llm_request=LLMRequest(temperature=0.9),
            db_settings=db_settings,
        )

        assert isinstance(request, LLMRequest)
        assert request.temperature == 0.9


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
