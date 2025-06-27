from abc import ABC
import json
import re
import types
from typing import (
    Any,
    Optional,
    Sequence,
    Union,
    Callable,
    cast,
)

from llama_index.core.agent.react.formatter import ReActChatFormatter
from llama_index.core.agent.react.output_parser import ReActOutputParser
from llama_index.core.agent.react.step import ReActAgentWorker
from llama_index.core.agent.runner.base import AgentRunner
from llama_index.core.callbacks import (
    CallbackManager,
)
from llama_index.core.llms.llm import LLM
from llama_index.core.memory.types import BaseMemory
from llama_index.core.objects.base import ObjectRetriever
from llama_index.core.tools import BaseTool, ToolOutput

from llama_index.core.agent import ReActAgent
from llama_index.core.memory import BaseMemory
from llama_index.core.agent.react.formatter import ReActChatFormatter

from airunner.utils.application import get_logger

ReActAgentMeta = type(ReActAgent)


class CustomReActAgentWorker(ReActAgentWorker):
    def __init__(
        self,
        tools: Sequence[BaseTool],
        llm: LLM,
        max_iterations: int = 10,
        react_chat_formatter: Optional[ReActChatFormatter] = None,
        output_parser: Optional[ReActOutputParser] = None,
        callback_manager: Optional[CallbackManager] = None,
        verbose: bool = False,
        tool_retriever: Optional[ObjectRetriever[BaseTool]] = None,
        handle_reasoning_failure_fn: Optional[
            Callable[[CallbackManager, Exception], ToolOutput]
        ] = None,
    ) -> None:
        self.tool_retriever = tool_retriever
        super().__init__(
            tools=tools,
            llm=llm,
            max_iterations=max_iterations,
            react_chat_formatter=react_chat_formatter,
            output_parser=output_parser,
            callback_manager=callback_manager,
            verbose=verbose,
            tool_retriever=tool_retriever,
            handle_reasoning_failure_fn=handle_reasoning_failure_fn,
        )

    def reinitialize_tools(
        self,
        tools: Optional[Union[list, tuple]] = None,
        tool_retriever: Optional[ObjectRetriever[BaseTool]] = None,
    ):
        tool_retriever = tool_retriever or self.tool_retriever
        if len(tools) > 0 and tool_retriever is not None:
            raise ValueError("Cannot specify both tools and tool_retriever")
        elif len(tools) > 0:
            self._get_tools = lambda _: tools
        elif tool_retriever is not None:
            tool_retriever_c = cast(ObjectRetriever[BaseTool], tool_retriever)
            self._get_tools = lambda message: tool_retriever_c.retrieve(
                message
            )
        else:
            self._get_tools = lambda _: []


class ReactAgentEngine(ReActAgent, ABC, metaclass=ReActAgentMeta):
    def __init__(
        self,
        tools: Sequence[BaseTool],
        llm: LLM,
        memory: BaseMemory,
        max_iterations: int = 10,
        react_chat_formatter: Optional[ReActChatFormatter] = None,
        output_parser: Optional[ReActOutputParser] = None,
        callback_manager: Optional[CallbackManager] = None,
        verbose: bool = False,
        tool_retriever: Optional[ObjectRetriever[BaseTool]] = None,
        context: Optional[str] = None,
        handle_reasoning_failure_fn: Optional[
            Callable[[CallbackManager, Exception], ToolOutput]
        ] = None,
    ) -> None:
        self._llm = llm
        self.logger = get_logger(__name__)
        """Init params."""
        callback_manager = callback_manager or llm.callback_manager
        if context and react_chat_formatter:
            raise ValueError(
                "Cannot provide both context and react_chat_formatter"
            )
        if context:
            react_chat_formatter = ReActChatFormatter.from_defaults(context)
            context = None

        super().__init__(
            tools=tools,
            llm=llm,
            memory=memory,
            max_iterations=max_iterations,
            react_chat_formatter=react_chat_formatter,
            output_parser=output_parser,
            callback_manager=callback_manager,
            verbose=verbose,
            tool_retriever=tool_retriever,
            context=context,
            handle_reasoning_failure_fn=handle_reasoning_failure_fn,
        )

        self.agent_worker = CustomReActAgentWorker.from_tools(
            tools=tools,
            tool_retriever=tool_retriever,
            llm=llm,
            max_iterations=max_iterations,
            react_chat_formatter=react_chat_formatter,
            output_parser=output_parser,
            callback_manager=callback_manager,
            verbose=verbose,
            handle_reasoning_failure_fn=handle_reasoning_failure_fn,
        )

    @classmethod
    def from_tools(cls, *args, formatter=None, **kwargs):
        """Create a ReactAgentEngine with the correct formatter (from_tools)."""
        if formatter is None:
            formatter = ReActChatFormatter.from_defaults()

        # Create the instance using parent's from_tools
        instance = super().from_tools(*args, formatter=formatter, **kwargs)

        # Ensure tools are properly accessible
        if args and hasattr(instance, "_tools"):
            # llama_index ReActAgent might store tools in _tools
            instance.tools = instance._tools
        elif args:
            # If tools are passed as first argument, store them directly
            tools_list = args[0] if len(args) == 1 else list(args)
            if isinstance(tools_list, (list, tuple)):
                instance.tools = tools_list

        return instance

    @property
    def memory(self) -> BaseMemory:
        return self._memory

    @memory.setter
    def memory(self, memory: BaseMemory):
        self._memory = memory

    def _refresh_tools(self, tools: Optional[Union[list, tuple]] = None):
        # BaseAgentWorker
        self.agent_worker

    def stream_chat(
        self,
        query_str: str,
        messages: Optional[Union[list, tuple]] = None,
        tool_choice: Optional[Union[str, dict]] = None,
        **kwargs: Optional[Any],
    ):
        # Store original tools for restoration later
        original_tools = getattr(self, "tools", [])

        if tool_choice:
            # Find the target tool
            target_tool = None
            for tool in original_tools:
                tool_name = getattr(
                    getattr(tool, "metadata", None), "name", None
                )
                if tool_name == tool_choice:
                    target_tool = tool
                    break

            if target_tool:
                self.agent_worker.reinitialize_tools(tools=[target_tool])
                enhanced_query = f"{query_str}\n\nUse the {tool_choice} tool to fulfill this request. Think carefully about the correct parameters."
                query_str = enhanced_query

        if hasattr(super(), "stream_chat"):
            result = super().stream_chat(
                query_str, chat_history=messages, tool_choice=tool_choice
            )
            # Parse for tool call and execute tool
            output = ""
            if hasattr(result, "response_gen"):
                for token in result.response_gen:
                    output += token
                    yield token  # Stream LLM output as usual
            else:
                output = str(result)
                yield output
            # Now, after streaming, check for tool call
            self.logger.info(f"[DEBUG] Full LLM output: {repr(output)}")
            self.logger.info(f"[DEBUG] Tool choice: {tool_choice}")
            self.logger.info(
                f"[DEBUG] Available tools: {[getattr(getattr(t, 'metadata', None), 'name', None) for t in self.tools]}"
            )

            # First try standard ReAct format: Action: tool_name\nAction Input: {...}
            tool_call_match = re.search(
                r"Action Input:\s*(\{[^}]*(?:\{[^}]*\}[^}]*)*\})",
                output,
                re.MULTILINE,
            )
            self.logger.info(f"[DEBUG] Action Input match: {tool_call_match}")

            # Fallback to simpler pattern if nested braces are too complex
            if not tool_call_match:
                tool_call_match = re.search(
                    r"Action Input:\s*(\{.*?\})",
                    output,
                    re.MULTILINE | re.DOTALL,
                )
                self.logger.info(
                    f"[DEBUG] Action Input simple match: {tool_call_match}"
                )

            # Fallback to legacy formats
            if not tool_call_match:
                tool_call_match = re.search(
                    r"Action:\s*```json\s*({[\s\S]+?})\s*```", output
                )
                self.logger.info(
                    f"[DEBUG] Action JSON match: {tool_call_match}"
                )
            if not tool_call_match:
                tool_call_match = re.search(r"Action:\s*({[\s\S]+?})", output)
                self.logger.info(
                    f"[DEBUG] Action fallback match: {tool_call_match}"
                )

            # Additional fallbacks for more flexible parsing
            if not tool_call_match:
                # Try to find JSON that contains expected action parameters
                action_json_match = re.search(
                    r'(\{[^}]*"action"[^}]*\})',
                    output,
                    re.MULTILINE | re.DOTALL,
                )
                if action_json_match:
                    tool_call_match = action_json_match
                    self.logger.info(
                        f"[DEBUG] Action parameter match: {tool_call_match}"
                    )

            if not tool_call_match:
                # Try to find any JSON with from_location/to_location for directions
                direction_json_match = re.search(
                    r'(\{[^}]*"from_location"[^}]*"to_location"[^}]*\})',
                    output,
                    re.MULTILINE | re.DOTALL,
                )
                if direction_json_match:
                    tool_call_match = direction_json_match
                    self.logger.info(
                        f"[DEBUG] Direction parameter match: {tool_call_match}"
                    )
            # Also match any JSON block if only one tool is available
            tool_name = tool_choice
            if not tool_call_match and len(self.tools) == 1:
                tool_call_match = re.search(
                    r"```json\s*({[\s\S]+?})\s*```", output
                )
                self.logger.info(
                    f"[DEBUG] JSON block match: {tool_call_match}"
                )
                if not tool_call_match:
                    tool_call_match = re.search(r"({[\s\S]+?})", output)
                    self.logger.info(
                        f"[DEBUG] Any JSON match: {tool_call_match}"
                    )
                tool_name = getattr(
                    getattr(self.tools[0], "metadata", None), "name", None
                )
            if tool_call_match:
                try:
                    tool_json = tool_call_match.group(1)
                    self.logger.info(
                        f"[DEBUG] Extracted tool JSON: {repr(tool_json)}"
                    )
                    # Try to clean up the JSON if needed
                    tool_json = tool_json.strip()
                    self.logger.info(
                        f"[DEBUG] Cleaned tool JSON: {repr(tool_json)}"
                    )
                    tool_args = json.loads(tool_json)
                    self.logger.info(f"[DEBUG] Parsed tool args: {tool_args}")
                    self.logger.info(f"[DEBUG] Tool name: {tool_name}")
                    # Try to infer tool name from context or tool_choice
                    if not tool_name:
                        # Try to find a tool name in the output (e.g., "use_browser_tool")
                        tool_name_match = re.search(
                            r"use_([a-z_]+)_tool", output
                        )
                        if tool_name_match:
                            tool_name = tool_name_match.group(0)
                    # Find the tool
                    tool = None
                    for t in self.tools:
                        tname = getattr(
                            getattr(t, "metadata", None), "name", None
                        )
                        if tname == tool_name:
                            tool = t
                            break
                    if tool:
                        self.logger.info(
                            f"[DEBUG] Found tool: {tool} with name: {tool_name}"
                        )
                        self.logger.info(
                            f"[DEBUG] Calling tool with args: {tool_args}"
                        )
                        tool_result = tool(**tool_args)
                        self.logger.info(f"[DEBUG] Tool result: {tool_result}")

                        # Store the last tool result for map tool access
                        if tool_name == "map_tool" and hasattr(
                            tool_result, "raw_output"
                        ):
                            # Store on self (the react agent engine), for the LLMGenerateWorker to access
                            self._last_map_tool_result = tool_result.raw_output
                            self.logger.info(
                                f"[DEBUG] Stored map tool result: {self._last_map_tool_result}"
                            )
                        elif tool_name == "map_tool":
                            self.logger.info(
                                f"[DEBUG] Map tool result has no raw_output: {tool_result}"
                            )
                            self.logger.info(
                                f"[DEBUG] Tool result attributes: {dir(tool_result)}"
                            )

                        # If the tool result is a generator, stream it
                        if isinstance(tool_result, types.GeneratorType):
                            for ttoken in tool_result:
                                yield ttoken
                        else:
                            # If the tool has a 'content' attribute, yield that
                            content = getattr(tool_result, "content", None)
                            if content is not None:
                                yield str(content)
                            else:
                                yield str(tool_result)
                    else:
                        self.logger.error(
                            f"[DEBUG] Tool not found: {tool_name}"
                        )
                except Exception as e:
                    self.logger.error(
                        f"Failed to execute tool: {e}. Tool JSON: {tool_json if 'tool_json' in locals() else 'N/A'}"
                    )
        # Always restore original tools list
        if tool_choice and original_tools:
            self.agent_worker.reinitialize_tools(tools=original_tools)
