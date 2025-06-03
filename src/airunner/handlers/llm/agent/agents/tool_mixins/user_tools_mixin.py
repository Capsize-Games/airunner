from typing import Annotated
from llama_index.core.tools import FunctionTool
from airunner.handlers.llm.agent.agents.tool_mixins.tool_singleton_mixin import (
    ToolSingletonMixin,
)


class UserToolsMixin(ToolSingletonMixin):
    """Mixin for user/information tools."""

    @property
    def information_scraper_tool(self):
        self.logger.info("information_scraper_tool called")

        def scrape_information(tag: str, information: str) -> str:
            self.logger.info(f"Scraping information for tag: {tag}")
            self.logger.info(f"Information: {information}")
            self._update_user(tag, information)
            data = self.user.data or {}
            data[tag] = [information] if tag not in data else data[tag] + [information]
            self._update_user("data", data)
            return "Information scraped."

        return self._get_or_create_singleton(
            "_information_scraper_tool",
            FunctionTool.from_defaults,
            scrape_information,
            return_direct=True,
        )

    @property
    def store_user_tool(self):
        def store_user_information(
            category: Annotated[
                str,
                (
                    "The category of the information to store. "
                    "Can be 'likes', 'dislikes', 'hobbies', 'interests', etc."
                ),
            ],
            information: Annotated[
                str,
                (
                    "The information to store. "
                    "This can be a string or a list of strings."
                ),
            ],
        ) -> str:
            data = self.user.data or {}
            data[category] = (
                [information]
                if category not in data
                else data[category] + [information]
            )
            self._update_user(category, information)
            return "User information updated."

        return self._get_or_create_singleton(
            "_store_user_tool",
            FunctionTool.from_defaults,
            store_user_information,
            return_direct=True,
        )
