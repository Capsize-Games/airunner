"""Manages LangChain tools for the AI Runner agent."""

from typing import List, Callable, Optional, Any

from airunner.utils.application.mediator_mixin import MediatorMixin
from airunner.components.application.gui.windows.main.settings_mixin import (
    SettingsMixin,
)
from airunner.components.llm.managers.tools import (
    ImageTools,
    FileTools,
    SystemTools,
    ConversationTools,
    AutonomousControlTools,
)
from airunner.enums import LLMActionType

# CRITICAL: Import tools to trigger ToolRegistry registration
# This MUST happen at module load time
from airunner.components.llm import tools  # noqa: F401


class ToolManager(
    MediatorMixin,
    SettingsMixin,
    ImageTools,
    FileTools,
    SystemTools,
    ConversationTools,
    AutonomousControlTools,
):
    """Manages LangChain tools for the AI Runner agent.

    This class is composed of specialized tool mixins that provide different
    categories of tools:
    - ImageTools: Image generation and manipulation
    - FileTools: File system operations
    - SystemTools: Application control
    - ConversationTools: Conversation management and search
    - AutonomousControlTools: Full autonomous application control

    NOTE: Most tools have been migrated to the new ToolRegistry system.
    The tools from RAGTools, KnowledgeTools, WebTools, UserDataTools,
    CodeTools, and AgentTools are now available via @tool decorator in
    airunner.components.llm.tools/
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

        NOTE: This method returns old mixin-based tools only.
        Tools from ToolRegistry are automatically available via the
        @tool decorator system and don't need to be returned here.

        Returns:
            List of tool functions from remaining mixins
        """
        tools = [
            # Core conversation tools
            self.clear_conversation_tool(),
            self.update_mood_tool(),
            # Image generation tools
            self.generate_image_tool(),
            self.clear_canvas_tool(),
            self.open_image_tool(),
            # File system tools
            self.list_files_tool(),
            self.read_file_tool(),
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
            enabled_tools = LLMTool.objects.filter_by(enabled=True) or []

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

    def get_tools_by_categories(self, categories: List) -> List[Callable]:
        """Get tools filtered by categories.

        Args:
            categories: List of ToolCategory enum values to include

        Returns:
            List of tool functions matching the specified categories
        """
        from airunner.components.llm.core.tool_registry import ToolRegistry

        if not categories:
            return []

        filtered_tools = []
        category_set = set(categories)
        print(
            f"[TOOL MANAGER DEBUG] Filtering for categories: {category_set}",
            flush=True,
        )
        print(
            f"[TOOL MANAGER DEBUG] Total tools in registry: {len(ToolRegistry.all())}",
            flush=True,
        )

        for tool_info in ToolRegistry.all().values():
            print(
                f"[TOOL MANAGER DEBUG] Checking tool {tool_info.name} (category={tool_info.category})",
                flush=True,
            )
            if tool_info.category in category_set:
                print(
                    f"[TOOL MANAGER DEBUG] Category MATCH! Getting tool function...",
                    flush=True,
                )
                # Get the actual tool function
                tool_func = self._get_tool_by_name(tool_info.name)
                if tool_func:
                    print(
                        f"[TOOL MANAGER DEBUG] Added tool: {tool_info.name}",
                        flush=True,
                    )
                    filtered_tools.append(tool_func)
                else:
                    print(
                        f"[TOOL MANAGER DEBUG] Tool function NOT FOUND for {tool_info.name}",
                        flush=True,
                    )

        print(
            f"[TOOL MANAGER DEBUG] Filtered result: {len(filtered_tools)} tools",
            flush=True,
        )
        self.logger.info(
            f"Filtered to {len(filtered_tools)} tools from "
            f"categories: {[c.value for c in categories]}"
        )
        return filtered_tools

    def _get_tool_by_name(self, name: str) -> Optional[Callable]:
        """Get tool function by name.

        Args:
            name: Tool function name

        Returns:
            Tool function or None if not found
        """
        from airunner.components.llm.core.tool_registry import ToolRegistry

        # First check the NEW ToolRegistry (for @tool decorated functions)
        tool_info = ToolRegistry.get(name)
        if tool_info:
            print(
                f"[TOOL MANAGER DEBUG] Found NEW tool in registry: {name}",
                flush=True,
            )
            return tool_info.func

        # Fallback to OLD mixin-based tools
        # Map tool names to their getter methods
        tool_getters = {
            "store_user_data": self.store_user_data_tool,
            "get_user_data": self.get_user_data_tool,
            "update_mood": self.update_mood_tool,
            "clear_conversation": self.clear_conversation_tool,
            "toggle_tts": self.toggle_tts_tool,
            "generate_image": self.generate_image_tool,
            "clear_canvas": self.clear_canvas_tool,
            "open_image": self.open_image_tool,
            "rag_search": self.rag_search_tool,
            "search_web": self.search_web_tool,
        }

        getter = tool_getters.get(name)
        if getter:
            print(
                f"[TOOL MANAGER DEBUG] Found OLD mixin tool: {name}",
                flush=True,
            )
            return getter()

        self.logger.warning(f"Tool getter not found for: {name}")
        return None
