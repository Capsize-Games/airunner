"""
Adapter to integrate new tool system with existing BaseAgent.

This provides a bridge between the old agent architecture and the new
decorator-based tool system, allowing gradual migration.
"""

from typing import List, Optional, Any

from llama_index.core.tools import FunctionTool

from airunner.components.llm.core.tool_executor import ToolExecutor
from airunner.components.llm.core.tool_registry import ToolCategory
from airunner.enums import LLMActionType
from airunner.settings import AIRUNNER_LOG_LEVEL
from airunner.utils.application import get_logger


class ToolAdapter:
    """
    Adapts new tool system for use with existing agents.

    Converts decorator-registered tools into llama_index FunctionTools
    that can be used by the existing agent infrastructure.
    """

    def __init__(
        self,
        agent: Any,
        api: Any,
        logger: Optional[Any] = None,
    ):
        """
        Initialize tool adapter.

        Args:
            agent: Agent instance
            api: API instance
            logger: Logger
        """
        self.agent = agent
        self.api = api
        self.logger = logger or get_logger(__name__, AIRUNNER_LOG_LEVEL)

        # Create tool executor with dependencies
        self.tool_executor = ToolExecutor(
            agent=agent,
            api=api,
            logger=logger,
        )

    def get_tools_for_action(
        self,
        action: LLMActionType,
    ) -> List[FunctionTool]:
        """
        Get tools appropriate for an action type.

        Args:
            action: Action type

        Returns:
            List of FunctionTool instances
        """
        # Map actions to categories
        action_category_map = {
            LLMActionType.CHAT: [
                ToolCategory.CHAT,
                ToolCategory.CONVERSATION,
                ToolCategory.SYSTEM,
            ],
            LLMActionType.GENERATE_IMAGE: [
                ToolCategory.IMAGE,
            ],
            LLMActionType.SEARCH: [
                ToolCategory.SEARCH,
                ToolCategory.FILE,
            ],
            LLMActionType.RAG_CHAT: [
                ToolCategory.RAG,
                ToolCategory.CHAT,
                ToolCategory.FILE,
            ],
            LLMActionType.APPLICATION_COMMAND: [
                ToolCategory.SYSTEM,
                ToolCategory.FILE,
            ],
            LLMActionType.FILE_INTERACTION: [
                ToolCategory.FILE,
            ],
        }

        categories = action_category_map.get(action, [ToolCategory.CHAT])

        try:
            tools = self.tool_executor.get_all_tools(categories)
            self.logger.debug(
                f"Loaded {len(tools)} tools for action {action.name}"
            )
            return tools
        except Exception as e:
            self.logger.error(f"Error loading tools: {e}", exc_info=True)
            return []

    def get_all_tools(self) -> List[FunctionTool]:
        """
        Get all available tools.

        Returns:
            List of all FunctionTool instances
        """
        return self.tool_executor.get_all_tools()
