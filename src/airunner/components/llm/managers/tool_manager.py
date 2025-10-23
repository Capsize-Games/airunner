"""Manages LangChain tools for the AI Runner agent."""

import logging
from typing import List, Callable, Optional, Any

from airunner.utils.application.mediator_mixin import MediatorMixin
from airunner.components.application.gui.windows.main.settings_mixin import (
    SettingsMixin,
)
from airunner.components.llm.managers.tools import (
    RAGTools,
    KnowledgeTools,
    ImageTools,
    FileTools,
    WebTools,
    CodeTools,
    SystemTools,
    UserDataTools,
    ConversationTools,
    AutonomousControlTools,
)
from airunner.enums import LLMActionType


class ToolManager(
    MediatorMixin,
    SettingsMixin,
    RAGTools,
    KnowledgeTools,
    ImageTools,
    FileTools,
    WebTools,
    CodeTools,
    SystemTools,
    UserDataTools,
    ConversationTools,
    AutonomousControlTools,
):
    """Manages LangChain tools for the AI Runner agent.

    This class is composed of specialized tool mixins that provide different
    categories of tools:
    - RAGTools: Document search and RAG functionality
    - KnowledgeTools: Knowledge management and memory
    - ImageTools: Image generation and manipulation
    - FileTools: File system operations
    - WebTools: Web search and scraping
    - CodeTools: Code execution and tool creation
    - SystemTools: Application control
    - UserDataTools: User data storage
    - ConversationTools: Conversation management and search
    - AutonomousControlTools: Full autonomous application control
    """

    def __init__(self, rag_manager: Optional[Any] = None):
        """Initialize the ToolManager.

        Args:
            rag_manager: Optional RAG manager instance for document search
        """
        self.rag_manager = rag_manager
        super().__init__()

    def get_all_tools(self) -> List[Callable]:
        """Get all available tools.

        Returns:
            List of all tool functions from all mixins
        """
        tools = [
            # Core conversation tools
            self.rag_search_tool(),
            self.clear_conversation_tool(),
            self.update_mood_tool(),
            # Image generation tools
            self.generate_image_tool(),
            self.clear_canvas_tool(),
            self.open_image_tool(),
            # Information & search tools
            self.search_web_tool(),
            self.search_knowledge_base_documents_tool(),
            self.list_files_tool(),
            self.read_file_tool(),
            # Data management tools
            self.store_user_data_tool(),
            self.get_user_data_tool(),
            self.save_to_knowledge_base_tool(),
            # Knowledge & memory tools
            self.record_knowledge_tool(),
            self.recall_knowledge_tool(),
            # Code & computation tools
            self.write_code_tool(),
            self.execute_python_tool(),
            self.calculator_tool(),
            # Meta tools (self-improvement)
            self.create_tool_tool(),
            # Web tools
            self.web_scraper_tool(),
            # System tools
            self.emit_signal_tool(),
            self.quit_application_tool(),
            self.toggle_tts_tool(),
            # Conversation management tools
            self.list_conversations_tool(),
            self.get_conversation_tool(),
            self.summarize_conversation_tool(),
            self.update_conversation_title_tool(),
            self.switch_conversation_tool(),
            self.create_new_conversation_tool(),
            self.search_conversations_tool(),
            self.delete_conversation_tool(),
            # Autonomous control tools
            self.get_application_state_tool(),
            self.schedule_task_tool(),
            self.set_application_mode_tool(),
            self.request_user_input_tool(),
            self.analyze_user_behavior_tool(),
            self.propose_action_tool(),
            self.monitor_system_health_tool(),
            self.log_agent_decision_tool(),
        ]

        # Add any custom tools from database
        tools.extend(self._load_custom_tools())

        return tools

    def _load_custom_tools(self) -> List[Callable]:
        """Load custom tools created by the agent from database.

        Returns:
            List of dynamically loaded tool functions
        """
        try:
            from airunner.components.llm.data.llm_tool import LLMTool

            custom_tools = []
            enabled_tools = LLMTool.objects.filter(enabled=True)

            for tool_record in enabled_tools:
                try:
                    # Compile and load the tool
                    tool_func = self._compile_custom_tool(tool_record)
                    if tool_func:
                        custom_tools.append(tool_func)
                except Exception as e:
                    self.logger.error(
                        f"Error loading custom tool '{tool_record.name}': {e}"
                    )

            return custom_tools
        except Exception as e:
            self.logger.error(f"Error loading custom tools: {e}")
            return []

    def _compile_custom_tool(self, tool_record) -> Optional[Callable]:
        """Compile a custom tool from database record.

        Args:
            tool_record: LLMTool database record

        Returns:
            Compiled tool function or None if compilation fails
        """
        try:
            from langchain.tools import tool

            # Create a namespace for execution
            namespace = {
                "tool": tool,
                "__name__": f"custom_tool_{tool_record.name}",
            }

            # Execute the code to define the function
            exec(tool_record.code, namespace)

            # Find the decorated function
            for item in namespace.values():
                if callable(item) and hasattr(item, "name"):
                    # Wrap to track usage
                    original_func = item

                    def tracked_tool(*args, **kwargs):
                        try:
                            result = original_func(*args, **kwargs)
                            tool_record.increment_usage(success=True)
                            return result
                        except Exception as e:
                            tool_record.increment_usage(
                                success=False, error=str(e)
                            )
                            raise

                    # Copy metadata
                    tracked_tool.name = original_func.name
                    tracked_tool.description = original_func.description

                    return tracked_tool

            return None
        except Exception as e:
            self.logger.error(
                f"Error compiling tool '{tool_record.name}': {e}"
            )
            return None

    def get_tools_for_action(self, action: Any) -> List[Callable]:
        """Get tools filtered by action type.

        Args:
            action: LLMActionType enum value

        Returns:
            List of tool functions appropriate for the action
        """
        # Common tools available for all actions
        common_tools = [
            self.store_user_data_tool(),
            self.get_user_data_tool(),
            self.update_mood_tool(),
        ]

        if action == LLMActionType.CHAT:
            # Chat mode: no image/RAG tools, just conversation tools
            return common_tools + [
                self.clear_conversation_tool(),
                self.toggle_tts_tool(),
            ]

        elif action == LLMActionType.GENERATE_IMAGE:
            # Image mode: focus on image generation tools
            return common_tools + [
                self.generate_image_tool(),
                self.clear_canvas_tool(),
                self.open_image_tool(),
            ]

        elif action == LLMActionType.PERFORM_RAG_SEARCH:
            # RAG mode: focus on search tools
            return common_tools + [
                self.rag_search_tool(),
                self.search_web_tool(),
            ]

        elif action == LLMActionType.APPLICATION_COMMAND:
            # Auto mode: all tools available
            return self.get_all_tools()

        else:
            # Default: return all tools
            return self.get_all_tools()
