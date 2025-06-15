from llama_index.core.tools import FunctionTool
from airunner.components.llm.managers.agent.agents.tool_mixins.tool_singleton_mixin import (
    ToolSingletonMixin,
)
from airunner.components.llm.managers.agent.tools.browser_tool import BrowserTool


class BrowserToolsMixin(ToolSingletonMixin):
    """Mixin for image-related tools."""

    @property
    def use_browser_tool(self):
        """
        Return a singleton instance of the real BrowserTool (not a FunctionTool) for agent toolchains.
        Ensures the ReAct agent can call the actual BrowserTool implementation.
        """
        if not hasattr(self, "_use_browser_tool_instance"):
            self._use_browser_tool_instance = BrowserTool.from_defaults(
                llm=getattr(self, "llm", None),
                agent=self,
                name="use_browser_tool",
                description="Navigate to a URL and extract/summarize web page content.",
                return_direct=True,
            )
        return self._use_browser_tool_instance

    @property
    def browser_tool(self):
        """Expose the BrowserTool as a FunctionTool for agent toolchains."""

        def browser_tool_func(url: str) -> str:
            # This will call the BrowserTool directly
            if hasattr(self, "_browser_tool_instance"):
                tool = self._browser_tool_instance
            else:
                # Fallback: create a new instance (should be avoided in production)
                tool = BrowserTool.from_defaults(
                    llm=getattr(self, "llm", None),
                    agent=self,
                )
                self._browser_tool_instance = tool
            result = tool.call(url=url)
            return (
                result.content if hasattr(result, "content") else str(result)
            )

        return self._get_or_create_singleton(
            "_browser_tool_functiontool",
            FunctionTool.from_defaults,
            browser_tool_func,
            name="browser_tool",
            description="Navigate to a URL and extract/summarize web page content.",
            return_direct=True,
        )
