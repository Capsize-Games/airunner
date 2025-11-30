"""Manages LangChain tools for the AI Runner agent."""

from typing import List, Callable, Optional, Any

from airunner.components.llm.managers.tools import (
    ImageTools,
    FileTools,
    SystemTools,
    ConversationTools,
    AutonomousControlTools,
)
from airunner.components.llm.core.tool_registry import ToolCategory
from airunner.enums import LLMActionType

# CRITICAL: Import tools to trigger ToolRegistry registration
# This MUST happen at module load time
from airunner.components.llm import tools  # noqa: F401


class ToolManager(
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

    def _wrap_tool_with_dependencies(self, tool_info):
        """Wrap a tool function with dependency injection for LangChain.

        Injects `api` and `agent` parameters if the tool requires them.

        Args:
            tool_info: ToolInfo instance from registry

        Returns:
            Wrapped function with dependencies injected
        """
        from airunner.components.server.api.server import get_api
        from functools import wraps

        @wraps(tool_info.func)
        def wrapped(*args, **kwargs):
            # Debug/logging: report invocation args for better diagnosis
            try:
                self.logger.debug(
                    f"[TOOL WRAPPER] Invoking tool: {tool_info.name} "
                    f"args={args} kwargs_keys={list(kwargs.keys())}"
                )
            except Exception:
                # logger might not always be available in unit tests
                print(
                    f"[TOOL WRAPPER] Invoking tool: {tool_info.name} "
                    f"args={args} kwargs_keys={list(kwargs.keys())}",
                    flush=True,
                )

            # Inject API if required (ALWAYS get from global, ignore kwargs)
            if tool_info.requires_api:
                # Remove api from kwargs if the model provided it (it will be None)
                kwargs.pop("api", None)
                # For RAG tools, inject rag_manager directly as api
                # Otherwise get API from rag_manager.api or global
                if tool_info.category == ToolCategory.RAG and self.rag_manager:
                    # RAG tools get the rag_manager directly (LLMModelManager with RAG methods)
                    api = self.rag_manager
                elif (
                    self.rag_manager
                    and hasattr(self.rag_manager, "api")
                    and self.rag_manager.api
                ):
                    api = self.rag_manager.api
                else:
                    api = get_api()

                if api is None:
                    return (
                        f"Error: API not available for tool {tool_info.name}"
                    )
                kwargs["api"] = api

            # Inject agent if required (not yet implemented)
            # if tool_info.requires_agent and self.agent:
            #     kwargs["agent"] = self.agent

            try:
                result = tool_info.func(*args, **kwargs)
                # Log/trace return value shape for diagnostics
                try:
                    truncated = repr(result)[:2000]
                except Exception:
                    print(
                        f"[TOOL WRAPPER] Tool {tool_info.name} returned: {repr(result)[:2000]}",
                        flush=True,
                    )
                return result
            except Exception as e:
                import traceback

                error_msg = f"Error executing {tool_info.name}: {str(e)}\n{traceback.format_exc()}"
                self.logger.error(error_msg)
                return f"Error: {str(e)}"

        return wrapped

    def get_all_tools(self, include_deferred: bool = True) -> List[Callable]:
        """Get all available tools.

        Returns tools from both:
        1. Old mixin-based tools (not yet migrated)
        2. New ToolRegistry decorated tools

        Args:
            include_deferred: If True, include all tools. If False, only
                immediate tools (defer_loading=False). Default is True for
                backward compatibility.

        Returns:
            List of all tool functions
        """
        from airunner.components.llm.core.tool_registry import ToolRegistry

        # Start with old mixin-based tools that haven't been migrated yet
        # NOTE: Tools commented out have been migrated to ToolRegistry
        tools = [
            # Core conversation tools
            self.clear_conversation_tool(),
            # self.update_mood_tool(),  # Migrated to ToolRegistry (mood_tools.py)
            # Image generation tools (migrated to ToolRegistry - commented out)
            # self.generate_image_tool(),
            # self.clear_canvas_tool(),
            # self.open_image_tool(),
            # File system tools
            self.list_files_tool(),
            # self.read_file_tool(),  # Migrated to ToolRegistry
            # System tools
            self.emit_signal_tool(),
            # self.quit_application_tool(),  # Migrated to ToolRegistry
            # self.toggle_tts_tool(),  # Migrated to ToolRegistry
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

        # Add new ToolRegistry decorated tools with dependency injection
        # Get either all tools or just immediate ones based on include_deferred
        if include_deferred:
            registry_tools = ToolRegistry.all()
        else:
            registry_tools = ToolRegistry.get_immediate_tools()

        # Wrap tools to inject api and agent parameters
        for tool_info in registry_tools.values():
            wrapped_func = self._wrap_tool_with_dependencies(tool_info)
            # Add .name and .description attributes like LangChain tools
            wrapped_func.name = tool_info.name
            wrapped_func.description = tool_info.description
            wrapped_func.return_direct = tool_info.return_direct
            # Keep the tool category for downstream filtering/diagnostics
            wrapped_func.category = getattr(tool_info, "category", None)
            tools.append(wrapped_func)

        # Add any custom tools from database
        tools.extend(self._load_custom_tools())

        return tools

    def get_immediate_tools(self) -> List[Callable]:
        """Get only immediately-available tools (defer_loading=False).

        Use this for reduced context size. Tools with defer_loading=True
        can be discovered via search_tools.

        Returns:
            List of immediate tool functions
        """
        return self.get_all_tools(include_deferred=False)

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
                    # Ensure compatibility with frameworks expecting .__name__ and return_direct
                    tracked_tool.__name__ = getattr(
                        original_func, "__name__", tracked_tool.name
                    )
                    tracked_tool.return_direct = getattr(
                        original_func, "return_direct", False
                    )

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
        # Use _get_tool_by_name to retrieve from ToolRegistry or mixin fallback
        common_tools = []
        for tool_name in ["store_user_data", "get_user_data", "update_mood"]:
            tool = self._get_tool_by_name(tool_name)
            if tool:
                common_tools.append(tool)

        if action == LLMActionType.CHAT:
            # Chat mode: no image/RAG tools, just conversation tools
            additional_tools = []
            for tool_name in ["clear_conversation", "toggle_tts"]:
                tool = self._get_tool_by_name(tool_name)
                if tool:
                    additional_tools.append(tool)
            return common_tools + additional_tools

        elif action == LLMActionType.GENERATE_IMAGE:
            # Image mode: focus on image generation tools
            additional_tools = []
            for tool_name in ["generate_image", "clear_canvas", "open_image"]:
                tool = self._get_tool_by_name(tool_name)
                if tool:
                    additional_tools.append(tool)
            return common_tools + additional_tools

        elif action == LLMActionType.PERFORM_RAG_SEARCH:
            # RAG mode: prefer any ToolRegistry tools that look like a search tool.
            additional_tools = []
            try:
                from airunner.components.llm.core.tool_registry import (
                    ToolRegistry,
                )

                for tool_info in ToolRegistry.all().values():
                    name_lower = (tool_info.name or "").lower()
                    category_lower = str(
                        getattr(tool_info, "category", "")
                    ).lower()

                    # Heuristic: search / rag / knowledge keywords indicate a true search tool
                    if (
                        "search" in name_lower
                        or "rag" in name_lower
                        or "knowledge" in name_lower
                        or "search" in category_lower
                    ):
                        wrapped = self._wrap_tool_with_dependencies(tool_info)
                        wrapped.name = tool_info.name
                        wrapped.description = tool_info.description
                        wrapped.return_direct = tool_info.return_direct
                        wrapped.category = getattr(tool_info, "category", None)
                        additional_tools.append(wrapped)
            except Exception:
                # fall back to explicit names if registry not available
                self.logger.debug(
                    "ToolRegistry unavailable while filtering search tools; falling back to hardcoded names"
                )

            # Fallback named tools in case registry doesn't cover them. This
            # captures older mixin tools and name variants.
            for tool_name in [
                "rag_search",
                "search_web",
                "search_knowledge_base_documents",
            ]:
                tool = self._get_tool_by_name(tool_name)
                if tool:
                    additional_tools.append(tool)

            return common_tools + additional_tools

        elif action == LLMActionType.APPLICATION_COMMAND:
            # Auto mode: all tools available
            return self.get_all_tools()

    def get_tools_by_categories(
        self, categories: List, include_deferred: bool = False
    ) -> List[Callable]:
        """Get tools filtered by categories.

        Args:
            categories: List of ToolCategory enum values to include
            include_deferred: If True, include tools with defer_loading=True.
                Default is False to reduce context size.

        Returns:
            List of tool functions matching the specified categories
        """
        from airunner.components.llm.core.tool_registry import ToolRegistry

        if not categories:
            return []

        filtered_tools = []
        seen_names = set()

        # Use get_by_category for each category to ensure lazy loading
        # is triggered for any missing categories
        for category in categories:
            for tool_info in ToolRegistry.get_by_category(category):
                # Skip deferred tools unless explicitly requested
                if tool_info.defer_loading and not include_deferred:
                    continue
                if tool_info.name not in seen_names:
                    seen_names.add(tool_info.name)
                    # Get the actual tool function
                    tool_func = self._get_tool_by_name(tool_info.name)
                    if tool_func:
                        filtered_tools.append(tool_func)

        self.logger.info(
            f"Filtered to {len(filtered_tools)} tools from "
            f"categories: {[c.value for c in categories]} "
            f"(include_deferred={include_deferred})"
        )
        return filtered_tools

    def _get_tool_by_name(self, name: str) -> Optional[Callable]:
        """Get a tool function by name from either ToolRegistry or mixins.

        Args:
            name: Tool function name

        Returns:
            Tool function or None if not found
        """
        from airunner.components.llm.core.tool_registry import ToolRegistry

        # First check the NEW ToolRegistry (for @tool decorated functions)
        tool_info = ToolRegistry.get(name)
        # Fuzzy/case-insensitive or partial match fallback against ToolRegistry
        if not tool_info:
            for t in ToolRegistry.all().values():
                # exact/case-insensitive match OR substring match
                if (t.name or "").lower() == name.lower() or name.lower() in (
                    t.name or ""
                ).lower():
                    tool_info = t
                    break
        if tool_info:
            # CRITICAL: Wrap with dependencies (API/Agent injection)
            wrapped_func = self._wrap_tool_with_dependencies(tool_info)

            # Add attributes to make it compatible with LangChain
            wrapped_func.name = tool_info.name
            wrapped_func.description = tool_info.description
            wrapped_func.return_direct = tool_info.return_direct
            wrapped_func.category = getattr(tool_info, "category", None)
            return wrapped_func

        # Fallback to OLD mixin-based tools
        # Map tool names to their getter methods
        tool_getters = {
            "update_mood": self.update_mood_tool,
            "clear_conversation": self.clear_conversation_tool,
            "toggle_tts": self.toggle_tts_tool,
            "generate_image": self.generate_image_tool,
            "clear_canvas": self.clear_canvas_tool,
            "open_image": self.open_image_tool,
        }

        getter = tool_getters.get(name)
        if getter:
            return getter()

        self.logger.warning(f"Tool getter not found for: {name}")
        return None
