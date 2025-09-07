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
            # Replace placeholders in context before creating formatter
            username = ""
            botname = ""
            try:
                if hasattr(self._llm, "agent") and self._llm.agent:
                    username = getattr(self._llm.agent, "username", "") or ""
                    botname = getattr(self._llm.agent, "botname", "") or ""
            except AttributeError:
                # Agent not set yet, will be handled later
                pass
            context = context.replace("{username}", username).replace(
                "{botname}", botname
            )
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
        # Note: we prefer to let ReAct produce the tool-call JSON first. We'll only
        # fallback to a direct image tool invocation if parsing fails below.

        # If a specific tool is explicitly requested, execute it directly and stream its result.
        # This guarantees that RAG (or any other tool) is actually used when the caller forces it.
        if isinstance(tool_choice, str) and original_tools:
            target_tool = None
            for tool in original_tools:
                try:
                    tname = getattr(
                        getattr(tool, "metadata", None), "name", None
                    )
                    if tname == tool_choice:
                        target_tool = tool
                        break
                except Exception:
                    continue

            if target_tool is not None:
                try:
                    # Build arguments for the tool
                    tool_args: dict = {"input": query_str}
                    # Forward llm_request/system_prompt when present
                    if isinstance(kwargs, dict):
                        if "llm_request" in kwargs:
                            tool_args["llm_request"] = kwargs["llm_request"]
                        if "system_prompt" in kwargs:
                            tool_args["system_prompt"] = kwargs[
                                "system_prompt"
                            ]

                    # Special-case: if RAG tool, prefer the agent's rag_system_prompt when available
                    if tool_choice == "rag_engine_tool":
                        try:
                            if (
                                hasattr(self, "_llm")
                                and self._llm
                                and hasattr(self._llm, "agent")
                                and getattr(
                                    self._llm.agent, "rag_system_prompt", None
                                )
                            ):
                                tool_args.setdefault(
                                    "system_prompt",
                                    self._llm.agent.rag_system_prompt,
                                )
                        except Exception:
                            pass

                    self.logger.debug(
                        f"[ReactAgentEngine] Directly executing tool '{tool_choice}' with args keys: {list(tool_args.keys())}"
                    )

                    tool_result = target_tool(**tool_args)

                    # Stream the result
                    import types as _types

                    if isinstance(tool_result, _types.GeneratorType):
                        for ttoken in tool_result:
                            if ttoken is None:
                                continue
                            yield ttoken
                        # Restore original tools and exit
                        if original_tools:
                            self.agent_worker.reinitialize_tools(
                                tools=original_tools
                            )
                        return
                    else:
                        content = getattr(tool_result, "content", None)
                        if content is not None:
                            yield str(content)
                        else:
                            yield str(tool_result)
                        if original_tools:
                            self.agent_worker.reinitialize_tools(
                                tools=original_tools
                            )
                        return
                except Exception as e:
                    self.logger.error(
                        f"[ReactAgentEngine] Direct tool execution failed for '{tool_choice}': {e}"
                    )

        if hasattr(super(), "stream_chat"):
            # Forward kwargs through to the parent stream_chat so downstream
            # formatters and steps can access contextual kwargs like username.
            # Remove tool_choice and chat_history from kwargs to avoid multiple values error
            # Only pass kwargs that are safe for the parent stream_chat method
            # ReActAgent.stream_chat accepts: message, chat_history, tool_choice
            safe_kwargs = {
                k: v
                for k, v in (kwargs or {}).items()
                if k
                in [
                    "message",
                    "chat_history",
                    "tool_choice",
                ]  # but tool_choice is handled separately
            }
            # Actually, since we're handling tool_choice and chat_history separately,
            # and message is positional, we can filter out everything except safe ones
            filtered_kwargs = {
                k: v
                for k, v in (kwargs or {}).items()
                if k
                not in [
                    "tool_choice",
                    "chat_history",
                    "input",
                    "query_str",
                    "messages",
                ]
            }
            result = super().stream_chat(
                query_str,
                chat_history=messages,
                tool_choice=tool_choice,
            )
            output = ""

            # Try multiple approaches to get streaming response
            if (
                hasattr(result, "response_gen")
                and result.response_gen is not None
            ):
                # Always yield tokens for real-time streaming, regardless of tool_choice
                for token in result.response_gen:
                    output += token
                    yield token
            elif hasattr(result, "response") and result.response:
                output = str(result.response)
                yield output
            else:
                output = str(result)
                yield output
            # Now, after streaming, check for tool call

            tool_call_match = re.search(
                r"Action:\s*```json\s*({[\s\S]+?})\s*```", output
            )
            if not tool_call_match:
                tool_call_match = re.search(r"Action:\s*({[\s\S]+?})", output)
            # Also match any JSON block if only one tool is available
            tool_name = tool_choice
            if not tool_call_match and len(self.tools) == 1:
                tool_call_match = re.search(
                    r"```json\s*({[\s\S]+?})\s*```", output
                )
                if not tool_call_match:
                    tool_call_match = re.search(r"({[\s\S]+?})", output)
                tool_name = getattr(
                    getattr(self.tools[0], "metadata", None), "name", None
                )
            if tool_call_match:
                try:
                    tool_json = tool_call_match.group(1)
                    tool_args = json.loads(tool_json)
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
                        self.logger.debug(
                            f"Executing tool: {tool_name} with args: {tool_args}"
                        )
                        tool_result = tool(**tool_args)
                        self.logger.debug(
                            f"Tool result type: {type(tool_result)}, result: {tool_result}"
                        )

                        # For image tool, suppress echoing tool output to avoid duplicate messages
                        tname = getattr(
                            getattr(tool, "metadata", None), "name", None
                        )
                        # if tname != "generate_image_tool":
                        if isinstance(tool_result, types.GeneratorType):
                            for ttoken in tool_result:
                                yield ttoken
                        else:
                            content = getattr(tool_result, "content", None)
                            self.logger.debug(
                                f"Tool result content: {content}"
                            )
                            if content is not None:
                                yield str(content)
                            else:
                                yield str(tool_result)
                except Exception as e:
                    self.logger.error(
                        f"Failed to execute tool: {e}. Tool JSON: {tool_json}"
                    )
            else:
                # No tool-call JSON found; if a specific tool was requested, fallback
                if tool_choice == "generate_image_tool":
                    # Find the tool by name
                    target_tool = None
                    for tool in original_tools:
                        tool_name = getattr(
                            getattr(tool, "metadata", None), "name", None
                        )
                        if tool_name == tool_choice:
                            target_tool = tool
                            break
                    if target_tool:
                        try:
                            prompt = query_str
                            fallback_args = {
                                "prompt": prompt,
                                "second_prompt": "",
                                "image_type": "Illustration",
                                "width": 1024,
                                "height": 1024,
                            }
                            _ = target_tool(**fallback_args)
                            # cleanup and exit early
                            if original_tools:
                                self.agent_worker.reinitialize_tools(
                                    tools=original_tools
                                )
                            return
                        except Exception as e:
                            self.logger.error(
                                f"Fallback direct image tool execution failed: {e}"
                            )
        # Always restore original tools list
        if tool_choice and original_tools:
            self.agent_worker.reinitialize_tools(tools=original_tools)

    def update_system_prompt(self, system_prompt: str):
        """
        Update the system prompt by modifying the formatter's system_header.
        """
        if (
            hasattr(self, "_step_engine")
            and self._step_engine
            and hasattr(self._step_engine, "_react_chat_formatter")
        ):
            # Try to get username and botname from the agent via LLM
            username = "User"
            botname = "Assistant"

            if (
                hasattr(self, "_llm")
                and self._llm
                and hasattr(self._llm, "agent")
            ):
                agent = self._llm.agent
                try:
                    username = agent.username or "User"
                except:
                    pass
                try:
                    botname = agent.botname or "Assistant"
                except:
                    pass

            # Replace {username} and {botname} placeholders
            system_prompt = system_prompt.replace("{username}", username)
            system_prompt = system_prompt.replace("{botname}", botname)
            self._step_engine._react_chat_formatter.system_header = (
                system_prompt
            )
