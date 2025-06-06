from abc import ABC

from llama_index.core.agent import ReActAgent
from llama_index.core.memory import BaseMemory
from llama_index.core.agent.react.formatter import ReActChatFormatter

from airunner.utils.application import get_logger

ReActAgentMeta = type(ReActAgent)


class ReactAgentEngine(ReActAgent, ABC, metaclass=ReActAgentMeta):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.logger = get_logger(__name__)

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

    def stream_chat(
        self, query_str, chat_history=None, tool_choice=None, **kwargs
    ):
        import re
        import json

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
                # Temporarily limit tools to only the target tool
                self.tools = [target_tool]
                # Update the internal ReAct agent's tools as well
                if hasattr(self, "_tools"):
                    self._tools = [target_tool]

                # Modify the query to be clearer about the task
                tool_description = getattr(
                    getattr(target_tool, "metadata", None),
                    "description",
                    f"use the {tool_choice} tool",
                )
                enhanced_query = f"{query_str}\n\nUse the {tool_choice} tool to fulfill this request. Think carefully about the correct parameters."
                query_str = enhanced_query

        try:
            if hasattr(super(), "stream_chat"):
                result = super().stream_chat(
                    query_str, chat_history=chat_history, **kwargs
                )
                # --- Patch: Parse for tool call and execute tool ---
                output = ""
                if hasattr(result, "response_gen"):
                    for token in result.response_gen:
                        output += token
                        yield token  # Stream LLM output as usual
                else:
                    output = str(result)
                    yield output
                # Now, after streaming, check for tool call
                import types

                tool_call_match = re.search(
                    r"Action:\s*```json\s*({[\s\S]+?})\s*```", output
                )
                if not tool_call_match:
                    tool_call_match = re.search(
                        r"Action:\s*({[\s\S]+?})", output
                    )
                # PATCH: Also match any JSON block if only one tool is available
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
                            tool_result = tool(**tool_args)
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
                    except Exception as e:
                        self.logger.error(
                            f"Failed to execute tool: {e}. Tool JSON: {tool_json}"
                        )
                return
            else:
                raise NotImplementedError(
                    "No stream_chat implementation found for ReactAgentEngine."
                )
        finally:
            # Always restore original tools list
            if tool_choice and original_tools:
                self.tools = original_tools
                if hasattr(self, "_tools"):
                    self._tools = original_tools
