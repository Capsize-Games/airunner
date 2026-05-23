"""Service-owned LangChain tool manager."""

import inspect
from typing import Any, Callable, List, Optional

from airunner_services.llm import tools  # noqa: F401
from airunner_services.llm.core.tool_registry import ToolCategory
from airunner_services.llm.managers.tools import (
    AutonomousControlTools,
    ConversationTools,
    FileTools,
    ImageTools,
    SystemTools,
)
from airunner_services.contract_enums import LLMActionType
from airunner_services.llm_workflow_events import (
    build_llm_tool_action_handler,
)


class ToolManager(
    ImageTools,
    FileTools,
    SystemTools,
    ConversationTools,
    AutonomousControlTools,
):
    """Manage LangChain tools for the AIRunner agent."""

    def __init__(
        self,
        rag_manager: Optional[Any] = None,
        tool_action_handler: Optional[Any] = None,
    ):
        self.rag_manager = rag_manager
        self._request_tool_defaults: dict[str, Any] = {}
        self._tool_action_handler = build_llm_tool_action_handler(
            action_handler=tool_action_handler,
            signal_emitter=rag_manager,
        )
        super().__init__(tool_action_handler=self._tool_action_handler)

    def set_request_tool_defaults(self, defaults: dict[str, Any]) -> None:
        """Set request-scoped default kwargs for tool calls."""
        self._request_tool_defaults = dict(defaults or {})

    def clear_request_tool_defaults(self) -> None:
        """Clear request-scoped tool default kwargs."""
        self._request_tool_defaults = {}

    def _wrap_tool_with_dependencies(self, tool_info):
        """Wrap one tool function with dependency injection for LangChain."""
        from airunner_services.api.legacy_server import get_api
        from functools import wraps

        sig = None
        accepted_kwargs = set()
        accepts_var_kwargs = False
        try:
            sig = inspect.signature(tool_info.func)
            for param in sig.parameters.values():
                if param.kind == inspect.Parameter.VAR_KEYWORD:
                    accepts_var_kwargs = True
                elif param.kind in (
                    inspect.Parameter.POSITIONAL_OR_KEYWORD,
                    inspect.Parameter.KEYWORD_ONLY,
                ):
                    accepted_kwargs.add(param.name)
        except Exception:
            sig = None

        @wraps(tool_info.func)
        def wrapped(*args, **kwargs):
            try:
                self.logger.debug(
                    f"[TOOL WRAPPER] Invoking tool: {tool_info.name} "
                    f"args={args} kwargs_keys={list(kwargs.keys())}"
                )
            except Exception:
                print(
                    f"[TOOL WRAPPER] Invoking tool: {tool_info.name} "
                    f"args={args} kwargs_keys={list(kwargs.keys())}",
                    flush=True,
                )

            if tool_info.requires_api:
                kwargs.pop("api", None)
                if tool_info.category == ToolCategory.RAG and self.rag_manager:
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

            if self._request_tool_defaults and (accepts_var_kwargs or sig):
                for key, value in self._request_tool_defaults.items():
                    if value is None or key in kwargs:
                        continue
                    if accepts_var_kwargs or key in accepted_kwargs:
                        kwargs[key] = value

            try:
                result = tool_info.func(*args, **kwargs)
                try:
                    repr(result)[:2000]
                except Exception:
                    print(
                        f"[TOOL WRAPPER] Tool {tool_info.name} returned: "
                        f"{repr(result)[:2000]}",
                        flush=True,
                    )
                return result
            except Exception as error:
                import traceback

                error_msg = (
                    f"Error executing {tool_info.name}: {str(error)}\n"
                    f"{traceback.format_exc()}"
                )
                self.logger.error(error_msg)
                return f"Error: {str(error)}"

        return wrapped

    def get_all_tools(self, include_deferred: bool = True) -> List[Callable]:
        """Return all available tools for the current request."""
        from airunner_services.llm.core.tool_registry import ToolRegistry

        tools = [
            self.clear_conversation_tool(),
            self.list_files_tool(),
            self.emit_signal_tool(),
            self.list_conversations_tool(),
            self.get_conversation_tool(),
            self.summarize_conversation_tool(),
            self.update_conversation_title_tool(),
            self.switch_conversation_tool(),
            self.create_new_conversation_tool(),
            self.search_conversations_tool(),
            self.delete_conversation_tool(),
            self.get_application_state_tool(),
            self.schedule_task_tool(),
            self.set_application_mode_tool(),
            self.request_user_input_tool(),
            self.analyze_user_behavior_tool(),
            self.propose_action_tool(),
            self.monitor_system_health_tool(),
            self.log_agent_decision_tool(),
        ]

        if include_deferred:
            registry_tools = ToolRegistry.all()
        else:
            registry_tools = ToolRegistry.get_immediate_tools()

        for tool_info in registry_tools.values():
            wrapped_func = self._wrap_tool_with_dependencies(tool_info)
            wrapped_func.name = tool_info.name
            wrapped_func.description = tool_info.description
            wrapped_func.return_direct = tool_info.return_direct
            wrapped_func.category = getattr(tool_info, "category", None)
            tools.append(wrapped_func)

        tools.extend(self._load_custom_tools())
        return tools

    def get_immediate_tools(self) -> List[Callable]:
        """Return only immediate tools with deferred ones excluded."""
        return self.get_all_tools(include_deferred=False)

    def _load_custom_tools(self) -> List[Callable]:
        """Load custom tools created by the agent from the database."""
        try:
            from airunner_services.llm.data.llm_tool import LLMTool

            custom_tools = []
            enabled_tools = LLMTool.objects.filter_by(enabled=True) or []

            for tool_record in enabled_tools:
                try:
                    if not getattr(tool_record, "safety_validated", False):
                        self.logger.warning(
                            "Skipping custom tool '%s': safety_validated is "
                            "false",
                            tool_record.name,
                        )
                        continue

                    tool_func = self._compile_custom_tool(tool_record)
                    if tool_func:
                        custom_tools.append(tool_func)
                except Exception as error:
                    self.logger.error(
                        f"Error loading custom tool '{tool_record.name}': "
                        f"{error}"
                    )

            return custom_tools
        except Exception as error:
            self.logger.error(f"Error loading custom tools: {error}")
            return []

    def _compile_custom_tool(self, tool_record) -> Optional[Callable]:
        """Compile one custom tool from its database record."""
        try:
            from langchain_core.tools import tool
            from airunner_services.llm.core.code_sandbox import (
                create_safe_builtins,
            )

            namespace = {
                "tool": tool,
                "__name__": f"custom_tool_{tool_record.name}",
                "__builtins__": create_safe_builtins(),
            }

            exec(tool_record.code, namespace)

            for item in namespace.values():
                if callable(item) and hasattr(item, "name"):
                    original_func = item

                    def tracked_tool(*args, **kwargs):
                        try:
                            result = original_func(*args, **kwargs)
                            tool_record.increment_usage(success=True)
                            return result
                        except Exception as error:
                            tool_record.increment_usage(
                                success=False,
                                error=str(error),
                            )
                            raise

                    tracked_tool.name = original_func.name
                    tracked_tool.description = original_func.description
                    tracked_tool.__name__ = getattr(
                        original_func,
                        "__name__",
                        tracked_tool.name,
                    )
                    tracked_tool.return_direct = getattr(
                        original_func,
                        "return_direct",
                        False,
                    )
                    return tracked_tool

            return None
        except Exception as error:
            self.logger.error(
                f"Error compiling tool '{tool_record.name}': {error}"
            )
            return None

    def get_tools_for_action(self, action: Any) -> List[Callable]:
        """Return the tools appropriate for one action type."""
        common_tools = []
        for tool_name in ["store_user_data", "get_user_data", "update_mood"]:
            tool = self._get_tool_by_name(tool_name)
            if tool:
                common_tools.append(tool)

        if action == LLMActionType.CHAT:
            additional_tools = []
            for tool_name in ["clear_conversation", "toggle_tts"]:
                tool = self._get_tool_by_name(tool_name)
                if tool:
                    additional_tools.append(tool)
            return common_tools + additional_tools

        if action == LLMActionType.GENERATE_IMAGE:
            additional_tools = []
            for tool_name in ["generate_image", "clear_canvas", "open_image"]:
                tool = self._get_tool_by_name(tool_name)
                if tool:
                    additional_tools.append(tool)
            return common_tools + additional_tools

        if action == LLMActionType.PERFORM_RAG_SEARCH:
            additional_tools = []
            try:
                from airunner_services.llm.core.tool_registry import (
                    ToolRegistry,
                )

                for tool_info in ToolRegistry.all().values():
                    name_lower = (tool_info.name or "").lower()
                    category_lower = str(
                        getattr(tool_info, "category", "")
                    ).lower()

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
                        wrapped.category = getattr(
                            tool_info,
                            "category",
                            None,
                        )
                        additional_tools.append(wrapped)
            except Exception:
                self.logger.debug(
                    "ToolRegistry unavailable while filtering search tools; "
                    "falling back to hardcoded names"
                )

            for tool_name in [
                "rag_search",
                "search_web",
                "search_knowledge_base_documents",
            ]:
                tool = self._get_tool_by_name(tool_name)
                if tool:
                    additional_tools.append(tool)

            return common_tools + additional_tools

        if action == LLMActionType.APPLICATION_COMMAND:
            return self.get_all_tools()

        return common_tools

    def get_tools_by_categories(
        self,
        categories: List,
        include_deferred: bool = False,
    ) -> List[Callable]:
        """Return tools filtered by the provided registry categories."""
        from airunner_services.llm.core.tool_registry import ToolRegistry

        if not categories:
            return []

        filtered_tools = []
        seen_names = set()

        for category in categories:
            for tool_info in ToolRegistry.get_by_category(category):
                if tool_info.defer_loading and not include_deferred:
                    continue
                if tool_info.name not in seen_names:
                    seen_names.add(tool_info.name)
                    tool_func = self._get_tool_by_name(tool_info.name)
                    if tool_func:
                        filtered_tools.append(tool_func)

        self.logger.info(
            f"Filtered to {len(filtered_tools)} tools from categories: "
            f"{[c.value for c in categories]} "
            f"(include_deferred={include_deferred})"
        )
        return filtered_tools

    def _get_tool_by_name(self, name: str) -> Optional[Callable]:
        """Return one tool function by name from the registry or mixins."""
        from airunner_services.llm.core.tool_registry import ToolRegistry

        tool_info = ToolRegistry.get(name)
        if not tool_info:
            for registry_tool in ToolRegistry.all().values():
                tool_name = (registry_tool.name or "").lower()
                if tool_name == name.lower() or name.lower() in tool_name:
                    tool_info = registry_tool
                    break
        if tool_info:
            wrapped_func = self._wrap_tool_with_dependencies(tool_info)
            wrapped_func.name = tool_info.name
            wrapped_func.description = tool_info.description
            wrapped_func.return_direct = tool_info.return_direct
            wrapped_func.category = getattr(tool_info, "category", None)
            return wrapped_func

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


__all__ = ["ToolManager"]