from airunner.components.llm.core.tool_registry import ToolRegistry, ToolCategory
from airunner.components.llm.tools.system_tools import get_current_datetime


class TestSystemTools:
    def test_get_current_datetime_is_registered(self):
        tool = ToolRegistry.get("get_current_datetime")

        assert tool is not None
        assert tool.category == ToolCategory.SYSTEM
        assert tool.return_direct is True

    def test_get_current_datetime_returns_local_datetime_text(self):
        result = get_current_datetime()

        assert "Current local date and time:" in result
        assert "Day:" in result
        assert "Timezone:" in result