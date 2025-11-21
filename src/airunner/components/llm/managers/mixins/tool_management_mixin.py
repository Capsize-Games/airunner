"""Tool management mixin for WorkflowManager.

Handles tool binding, compact schema generation, and tool configuration.
"""

from typing import List, Callable

from airunner.settings import AIRUNNER_LOG_LEVEL
from airunner.utils.application import get_logger


class ToolManagementMixin:
    """Manages tool binding and compact schema generation for workflows."""

    def __init__(self):
        """Initialize tool management mixin."""
        self.logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)
        self._tools: List[Callable] = []
        self._chat_model = None
        self._original_chat_model = None

    def _initialize_model(self):
        """
        Configure model for tool calling using ReAct pattern.

        Instead of dumping full tool schemas (which overwhelms models), we:
        1. Bind tools to chat model for native function calling (if supported)
        2. For local models, add COMPACT tool list to system prompt
        3. Let LangGraph's ToolNode handle parsing and execution
        """
        # Reset to original unbound model
        self._chat_model = self._original_chat_model

        # Skip if no tools provided
        if not self._tools or len(self._tools) == 0:
            self.logger.info("No tools provided - skipping tool binding")
            return

        # Log tool calling mode for debugging
        tool_calling_mode = self._get_tool_calling_mode()
        self.logger.debug("Model tool_calling_mode: %s", tool_calling_mode)

        # Try to bind tools for native function calling
        if hasattr(self._chat_model, "bind_tools"):
            self._bind_tools_to_model()
        elif self._tools:
            self.logger.warning(
                f"Chat model does not support bind_tools() - tools will not be available"
            )

    def _get_tool_calling_mode(self) -> str:
        """Get the tool calling mode from the chat model.

        Returns:
            Tool calling mode string (react, json, native)
        """
        return getattr(self._chat_model, "tool_calling_mode", "react")

    def _bind_tools_to_model(self):
        """Bind tools to the chat model using bind_tools().

        Handles exceptions gracefully and provides informative logging.
        """
        try:
            # Check if tool_choice was set via update_tools()
            tool_choice = getattr(self, "_tool_choice", None)

            if tool_choice:
                self._chat_model = self._chat_model.bind_tools(
                    self._tools, tool_choice=tool_choice
                )
                self.logger.info(
                    "Successfully bound %s tools to chat model with tool_choice='%s'",
                    len(self._tools),
                    tool_choice,
                )
            else:
                self._chat_model = self._chat_model.bind_tools(self._tools)
                self.logger.info(
                    "Successfully bound %s tools to chat model",
                    len(self._tools),
                )
            self.logger.debug("Tools bound successfully via bind_tools()")

            # NOTE: Tool instructions are added in _call_model() on each generation,
            # not here in init. This is because update_system_prompt() can overwrite
            # self._system_prompt, and we need tool instructions re-added each time.
            # See _call_model() line ~769 for the actual injection point.

        except NotImplementedError:
            self.logger.info(
                "Model doesn't support native function calling - "
                "using LangChain ReAct pattern"
            )
            # NOTE: Tool instructions are added in _call_model(), not here.
            # This prevents duplicate tool lists when system prompt is updated.

        except Exception as e:
            import traceback

            self.logger.warning(
                f"Could not bind tools: {type(e).__name__}: {e}"
            )
            self.logger.debug(f"Traceback: {traceback.format_exc()}")

    def _create_compact_tool_list(self) -> str:
        """
        Create a compact, readable tool list instead of verbose schemas.

        Instead of:
            ```
            @tool
            def generate_image(...):
                '''Long docstring...'''
                Args:
                    prompt (str): ...
                    width (int): ...
            ```

        We generate:
            Available tools:
            - generate_image(prompt, width, height) - Generate an image from text
            - search_documents(query, max_results) - Search knowledge base

        This is:
        - Much more compact (~50 tokens vs 500+ per tool)
        - Easier for models to parse
        - Standard ReAct pattern

        Returns:
            Formatted tool list string with usage instructions
        """
        if not self._tools:
            return ""

        tool_descriptions = self._build_tool_descriptions()
        mode_instructions = self._get_mode_instructions()

        result = "\n".join(tool_descriptions + [mode_instructions])
        self.logger.debug(
            f"Compact tool list ({self._get_tool_calling_mode()} mode): {len(result)} chars vs ~{len(self._tools) * 500} for full schemas"
        )
        return result

    def _build_tool_descriptions(self) -> List[str]:
        """Build list of tool descriptions with signatures.

        Returns:
            List of formatted tool description strings
        """
        descriptions = [
            "You have access to the following tools:",
            "",
            "IMPORTANT: Decide whether to use a tool based on what the user asks for.",
            "",
            "Use tools when the user wants you to PERFORM AN ACTION:",
            "  - Create, update, delete data (calendar events, files, etc.)",
            "  - Generate content (images, code, etc.)",
            "  - Search or retrieve information from external sources",
            "  - Execute commands or operations",
            "",
            "DO NOT use tools for simple conversation:",
            "  - Greetings: 'Hello', 'Hi', 'How are you?'",
            "  - Acknowledgments: 'Thanks', 'OK', 'Got it'",
            "  - General questions about yourself: 'What can you do?', 'Who are you?'",
            "",
        ]

        for tool in self._tools:
            tool_name = self._get_tool_name(tool)
            tool_desc = self._get_tool_description(tool, tool_name)
            param_str = self._get_tool_parameters(tool)
            short_desc = self._shorten_description(tool_desc)

            # Format: - tool_name(arg1, arg2) - Short description
            descriptions.append(f"- {tool_name}({param_str}) - {short_desc}")

        descriptions.append("")
        return descriptions

    def _get_tool_name(self, tool: Callable) -> str:
        """Extract tool name from tool object.

        Args:
            tool: Tool callable or StructuredTool object

        Returns:
            Tool name string
        """
        # StructuredTool objects have .name attribute but not .__name__
        tool_name = getattr(tool, "name", None)
        if tool_name is None:
            # Fallback for regular functions
            tool_name = getattr(tool, "__name__", "unknown_tool")
        return tool_name

    def _get_tool_description(self, tool: Callable, tool_name: str) -> str:
        """Get tool description from tool object or registry.

        Args:
            tool: Tool callable
            tool_name: Name of the tool

        Returns:
            Tool description string
        """
        # Try to get description from tool object first
        tool_desc = getattr(tool, "description", "")

        # If no description, try to look up in ToolRegistry
        if not tool_desc:
            from airunner.components.llm.core.tool_registry import ToolRegistry

            tool_info = ToolRegistry.get(tool_name)
            if tool_info:
                tool_desc = tool_info.description

        return tool_desc

    def _get_tool_parameters(self, tool: Callable) -> str:
        """Extract parameter signature from tool.

        Args:
            tool: Tool callable

        Returns:
            Comma-separated parameter string
        """
        import inspect

        if hasattr(tool, "func"):
            sig = inspect.signature(tool.func)
            params = [
                p
                for p in sig.parameters.keys()
                if p not in ["api", "agent", "self"]
            ]
            return ", ".join(params)
        elif hasattr(tool, "__name__"):
            # Try to get signature from the tool itself if it's a function
            try:
                sig = inspect.signature(tool)
                params = [
                    p
                    for p in sig.parameters.keys()
                    if p not in ["api", "agent", "self"]
                ]
                return ", ".join(params)
            except (ValueError, TypeError):
                return "..."
        else:
            return "..."

    def _shorten_description(self, description: str) -> str:
        """Shorten description to first sentence.

        Args:
            description: Full description string

        Returns:
            First sentence or "No description"
        """
        if description:
            return description.split(".")[0]
        return "No description"

    def _get_mode_instructions(self) -> str:
        """Get mode-specific tool calling instructions.

        Returns:
            Formatted instruction string based on tool calling mode
        """
        tool_calling_mode = self._get_tool_calling_mode()

        if tool_calling_mode == "json":
            return self._get_json_mode_instructions()
        elif tool_calling_mode == "native":
            return self._get_native_mode_instructions()
        else:
            return self._get_react_mode_instructions()

    def _get_json_mode_instructions(self) -> str:
        """Get instructions for JSON tool calling mode.

        Returns:
            JSON mode instruction string
        """
        return (
            "To use a tool, respond with ONLY valid JSON (RFC 8259 compliant) on a SINGLE LINE:\n"
            "- Use DOUBLE QUOTES for all strings (not single quotes)\n"
            '- Escape special characters: \\n for newline, \\" for quote, \\\\ for backslash\n'
            '- Format: {"tool": "tool_name", "arguments": {"arg1": "value1"}}\n\n'
            "CRITICAL examples for code strings - note the DOUBLE QUOTES:\n"
            '{"tool": "sympy_compute", "arguments": {"code": "import sympy as sp\\nx = sp.symbols(\\"x\\")\\nresult = sp.solve(x**2 - 4, x)"}}\n'
            '{"tool": "python_compute", "arguments": {"code": "result = 2 + 2"}}\n\n'
            "More examples:\n"
            '{"tool": "search_web", "arguments": {"query": "Python tutorials"}}\n\n'
            "To use MULTIPLE tools, output multiple JSON objects, one per line:\n"
            '{"tool": "sympy_compute", "arguments": {"code": "x = 1"}}\n'
            '{"tool": "sympy_compute", "arguments": {"code": "result = x + 1"}}\n\n'
            "After tool execution, you'll receive results and can provide your final answer."
        )

    def _get_native_mode_instructions(self) -> str:
        """Get instructions for native tool calling mode.

        Returns:
            Native mode instruction string
        """
        return (
            "Use tools when needed. You can use multiple tools at once if the task requires it. "
            "The system will handle tool execution automatically."
        )

    def _get_react_mode_instructions(self) -> str:
        """Get instructions for ReAct tool calling mode.

        Returns:
            ReAct mode instruction string
        """
        return (
            "To use a tool, respond EXACTLY in this format:\n"
            "Action: tool_name\n"
            'Action Input: {"arg1": "value1", "arg2": "value2"}\n\n'
            "To use multiple tools, you can specify them sequentially:\n"
            "Action: first_tool\n"
            'Action Input: {"arg": "value"}\n'
            "Action: second_tool\n"
            'Action Input: {"arg": "value"}\n\n'
            "After using a tool, you'll receive:\n"
            "Observation: [tool result]\n\n"
            "Then continue reasoning or provide your final answer."
        )

    def update_tools(self, tools: List[Callable], tool_choice: str = None):
        """Update the tools and rebuild the workflow.

        Args:
            tools: List of LangChain tool callables
            tool_choice: Optional tool_choice parameter ("any", "auto", "required", etc.)
        """
        self.logger.debug("Updating tools: %s tools provided", len(tools))
        for tool in tools:
            self.logger.debug("Tool: %s", getattr(tool, "__name__", str(tool)))
        self._tools = tools
        self._tool_choice = (
            tool_choice  # Store for use in _bind_tools_to_model
        )
        self._initialize_model()  # Re-bind tools
        self._build_and_compile_workflow()
