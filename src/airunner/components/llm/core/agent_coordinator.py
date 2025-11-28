"""
Agent coordinator - simplified agent management.

This replaces the overly complex BaseAgent with a clean, focused coordinator
that delegates to specialized handlers.
"""

from typing import Optional, Any, Dict, List

from llama_index.core.chat_engine.types import AgentChatResponse
from llama_index.core.llms.llm import LLM
from llama_index.core.memory import BaseMemory

from airunner.components.llm.core.tool_executor import ToolExecutor
from airunner.components.llm.core.request_processor import RequestProcessor
from airunner.components.llm.core.tool_registry import ToolCategory
from airunner.components.llm.managers.llm_request import LLMRequest
from airunner.components.llm.managers.llm_settings import LLMSettings
from airunner.enums import LLMActionType
from airunner.utils.application.mediator_mixin import MediatorMixin
from airunner.components.application.gui.windows.main.settings_mixin import (
    SettingsMixin,
)


# Import tools to register them


class AgentCoordinator(MediatorMixin, SettingsMixin):
    """
    Coordinates LLM requests, tools, and responses.

    Simplified replacement for BaseAgent that focuses on:
    - Clean request processing
    - Proper tool execution
    - Clear response handling
    """

    def __init__(
        self,
        llm: Optional[LLM] = None,
        memory: Optional[BaseMemory] = None,
        llm_settings: Optional[LLMSettings] = None,
        chat_engine: Optional[Any] = None,
    ):
        """
        Initialize agent coordinator.

        Args:
            llm: Language model instance
            memory: Conversation memory
            llm_settings: LLM configuration
            chat_engine: Chat engine for responses
        """
        super().__init__()

        self.llm = llm
        self.memory = memory
        self.llm_settings = llm_settings or LLMSettings()
        self.chat_engine = chat_engine

        # Initialize components
        self.tool_executor = ToolExecutor(
            agent=self,
            api=self.api,
            logger=self.logger,
        )

        self.request_processor = RequestProcessor(
            default_settings=self.generator_settings,
            logger=self.logger,
        )

        self._interrupt_flag = False

    def get_tools(
        self,
        action: LLMActionType = LLMActionType.CHAT,
    ) -> List[Any]:
        """
        Get tools appropriate for the action type.

        Args:
            action: Type of action to get tools for

        Returns:
            List of configured tools
        """
        # Map actions to tool categories
        category_map = {
            LLMActionType.CHAT: [
                ToolCategory.CHAT,
                ToolCategory.CONVERSATION,
                ToolCategory.SYSTEM,
                ToolCategory.PROJECT,  # Long-running project tools
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
        }

        categories = category_map.get(action, [ToolCategory.CHAT])
        return self.tool_executor.get_all_tools(categories)

    def chat(
        self,
        message: str,
        action: LLMActionType = LLMActionType.CHAT,
        llm_request: Optional[LLMRequest] = None,
        system_prompt: Optional[str] = None,
        extra_context: Optional[Dict[str, Dict]] = None,
        **kwargs,
    ) -> AgentChatResponse:
        """
        Process a chat message.

        Args:
            message: User message
            action: Action type
            llm_request: Request configuration
            system_prompt: Optional system prompt override
            extra_context: Additional context for the request
            **kwargs: Additional arguments

        Returns:
            Agent response
        """
        self.logger.debug(f"Processing chat request: action={action}")

        # Reset interrupt flag
        self._interrupt_flag = False

        # Prepare request
        request = self.request_processor.prepare_request(
            prompt=message,
            action=action,
            llm_request=llm_request,
            db_settings=self.generator_settings,
        )

        # Get appropriate tools
        tools = self.get_tools(action)

        # Execute with chat engine
        if not self.chat_engine:
            self.logger.error("No chat engine available")
            return self._create_error_response("Chat engine not initialized")

        try:
            # Update chat engine with tools
            if hasattr(self.chat_engine, "update_tools"):
                self.chat_engine.update_tools(tools)

            # Execute chat
            response = self.chat_engine.chat(
                message=message,
                chat_history=self.memory.get() if self.memory else None,
            )

            return response

        except Exception as e:
            self.logger.error(f"Error in chat: {e}", exc_info=True)
            return self._create_error_response(str(e))

    def interrupt(self):
        """Interrupt ongoing processing."""
        self._interrupt_flag = True
        self.logger.info("Agent interrupted")

    def clear_history(self, data: Optional[Dict] = None):
        """
        Clear conversation history.

        Args:
            data: Optional conversation data
        """
        if self.memory:
            self.memory.reset()
        self.logger.info("History cleared")

    def unload(self):
        """Clean up resources."""
        self.memory = None
        self.chat_engine = None
        self.llm = None
        self.logger.info("Agent coordinator unloaded")

    def _create_error_response(self, message: str) -> AgentChatResponse:
        """
        Create an error response.

        Args:
            message: Error message

        Returns:
            Error response
        """
        return AgentChatResponse(
            response=f"Error: {message}",
            sources=[],
        )
