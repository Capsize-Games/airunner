from typing import Annotated
from llama_index.core.tools import FunctionTool
from airunner.handlers.llm.agent.agents.tool_mixins.tool_singleton_mixin import (
    ToolSingletonMixin,
)


class BrowserToolsMixin(ToolSingletonMixin):
    """Mixin for image-related tools."""

    @property
    def use_browser_tool(self):
        if not hasattr(self, "_use_browser_tool"):

            def use_browser_tool(
                url: Annotated[
                    str,
                    ("The URL of the website you want to navigate to. "),
                ],
            ) -> str:
                print(
                    "CALLING USE_BROWSER_TOOL FROM BROWSERTOOLSMIXIN WITH URL:",
                    url,
                )
                self.api.browser.navigate_to_url(url)
                return "Navigating to URL..."

            # Make the description very explicit for the LLM
            self._use_browser_tool = FunctionTool.from_defaults(
                use_browser_tool,
                return_direct=True,
            )
        return self._use_browser_tool

    @property
    def browser_tool(self):
        """Expose the BrowserTool as a FunctionTool for agent toolchains."""
        from airunner.handlers.llm.agent.tools.browser_tool import BrowserTool

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
