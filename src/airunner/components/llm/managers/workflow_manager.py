import logging
from typing import Any, Annotated, Optional, List, Callable
from typing_extensions import TypedDict

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import (
    HumanMessage,
    AIMessage,
    BaseMessage,
    trim_messages,
)
from langchain_core.messages.utils import count_tokens_approximately
from langgraph.graph import START, END, StateGraph, add_messages
from langgraph.prebuilt import ToolNode

from airunner.components.llm.managers.database_checkpoint_saver import (
    DatabaseCheckpointSaver,
)


class WorkflowState(TypedDict):
    """State schema for the workflow."""

    messages: Annotated[list[BaseMessage], add_messages]


class WorkflowManager:
    """Manages the LangGraph workflow for agent execution."""

    def __init__(
        self,
        system_prompt: str,
        chat_model: Any,
        tools: Optional[List[Callable]] = None,
        max_tokens: int = 2000,
        conversation_id: Optional[int] = None,
    ):
        """
        Initialize the workflow manager.

        Args:
            system_prompt: System prompt for the agent
            chat_model: LangChain ChatModel instance (ChatHuggingFaceLocal, ChatOllama, etc.)
            tools: List of LangChain tools
            max_tokens: Maximum tokens for conversation history
            conversation_id: Optional conversation ID for persistence
        """
        self._system_prompt = system_prompt
        self._chat_model = chat_model
        self._tools = tools or []
        self._max_tokens = max_tokens
        self._token_counter = lambda msgs: count_tokens_approximately(msgs)
        self._conversation_id = conversation_id
        self._memory = DatabaseCheckpointSaver(conversation_id)
        self._thread_id = (
            str(conversation_id) if conversation_id else "default"
        )
        self._workflow = None
        self._compiled_workflow = None
        self._token_callback: Optional[Callable[[str], None]] = None
        self._interrupted = False
        self.logger = logging.getLogger(__name__)

        self._initialize_model()
        self._build_and_compile_workflow()

    def _initialize_model(self):
        """
        Configure model for tool calling using ReAct pattern.

        Instead of dumping full tool schemas (which overwhelms models), we:
        1. Bind tools to chat model for native function calling (if supported)
        2. For local models, add COMPACT tool list to system prompt
        3. Let LangGraph's ToolNode handle parsing and execution
        """
        # Skip if no tools provided
        if not self._tools or len(self._tools) == 0:
            self.logger.info("No tools provided - skipping tool binding")
            return

        # Try to bind tools for native function calling
        if hasattr(self._chat_model, "bind_tools"):
            try:
                self._chat_model = self._chat_model.bind_tools(self._tools)
                self.logger.info(
                    f"Successfully bound {len(self._tools)} tools to chat model"
                )

                # For local models without native function calling,
                # add COMPACT tool descriptions (not full schemas)
                if hasattr(self._chat_model, "get_tool_schemas_text"):
                    # Create compact tool list instead of verbose schemas
                    compact_tools = self._create_compact_tool_list()
                    if compact_tools:
                        self._system_prompt = (
                            f"{self._system_prompt}\n\n{compact_tools}"
                        )
                        self.logger.info(
                            f"Added compact tool list ({len(self._tools)} tools) to system prompt"
                        )

            except NotImplementedError:
                self.logger.info(
                    "Model doesn't support native function calling - "
                    "using LangChain ReAct pattern"
                )
                # Add compact tool list for ReAct pattern
                compact_tools = self._create_compact_tool_list()
                if compact_tools:
                    self._system_prompt = (
                        f"{self._system_prompt}\n\n{compact_tools}"
                    )
                    self.logger.info(
                        f"Added ReAct tool list ({len(self._tools)} tools)"
                    )

            except Exception as e:
                import traceback

                self.logger.warning(
                    f"Could not bind tools: {type(e).__name__}: {e}"
                )
                self.logger.debug(f"Traceback: {traceback.format_exc()}")
        elif self._tools:
            self.logger.warning(
                f"Chat model does not support bind_tools() - tools will not be available"
            )

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
        """
        if not self._tools:
            return ""

        tool_descriptions = []
        tool_descriptions.append("You have access to the following tools:")
        tool_descriptions.append("")

        for tool in self._tools:
            # Get tool metadata
            # StructuredTool objects have .name attribute but not .__name__
            tool_name = getattr(tool, "name", None)
            if tool_name is None:
                # Fallback for regular functions
                tool_name = getattr(tool, "__name__", "unknown_tool")

            tool_desc = getattr(tool, "description", "")

            # Extract function signature
            if hasattr(tool, "func"):
                import inspect

                sig = inspect.signature(tool.func)
                params = [
                    p
                    for p in sig.parameters.keys()
                    if p not in ["api", "agent", "self"]
                ]
                param_str = ", ".join(params)
            else:
                param_str = "..."

            # Clean description (first sentence only)
            short_desc = (
                tool_desc.split(".")[0] if tool_desc else "No description"
            )

            # Format: - tool_name(arg1, arg2) - Short description
            tool_descriptions.append(
                f"- {tool_name}({param_str}) - {short_desc}"
            )

        tool_descriptions.append("")

        # Add mode-specific instructions based on chat model's tool calling mode
        tool_calling_mode = getattr(
            self._chat_model, "tool_calling_mode", "react"
        )

        if tool_calling_mode == "json":
            # JSON mode: Clean structured output
            tool_descriptions.append(
                "To use a tool, respond with ONLY a JSON object (no markdown, no explanation):\n"
                '{"tool": "tool_name", "arguments": {"arg1": "value1", "arg2": "value2"}}\n\n'
                "Examples:\n"
                '{"tool": "search_web", "arguments": {"query": "Python tutorials"}}\n'
                '{"tool": "generate_image", "arguments": {"prompt": "sunset", "size": "1024x1024"}}\n\n'
                "After the tool executes, you'll receive the result and can continue the conversation."
            )
        elif tool_calling_mode == "native":
            # Native mode: Minimal instructions (tokenizer handles it)
            tool_descriptions.append(
                "Use tools when needed. The system will handle tool execution automatically."
            )
        else:
            # ReAct mode: Action/Observation format (fallback)
            tool_descriptions.append(
                "To use a tool, respond EXACTLY in this format:\n"
                "Action: tool_name\n"
                'Action Input: {"arg1": "value1", "arg2": "value2"}\n\n'
                "After using a tool, you'll receive:\n"
                "Observation: [tool result]\n\n"
                "Then continue reasoning or provide your final answer."
            )

        result = "\n".join(tool_descriptions)
        self.logger.debug(
            f"Compact tool list ({tool_calling_mode} mode): {len(result)} chars vs ~{len(self._tools) * 500} for full schemas"
        )
        return result

    def _build_and_compile_workflow(self):
        """Build and compile the LangGraph workflow."""
        self._workflow = self._build_graph()
        self._compiled_workflow = self._workflow.compile(
            checkpointer=self._memory
        )

    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow."""
        workflow = StateGraph(WorkflowState)

        workflow.add_node("model", self._call_model)
        if self._tools:
            workflow.add_node("tools", ToolNode(self._tools))

        workflow.add_edge(START, "model")

        if self._tools:
            workflow.add_conditional_edges(
                "model",
                self._route_after_model,
                {
                    "tools": "tools",
                    "end": END,
                },
            )
            workflow.add_edge("tools", "model")
        else:
            workflow.add_edge("model", END)

        return workflow

    def _route_after_model(self, state: WorkflowState) -> str:
        """Route to tools if model made tool calls, otherwise end."""
        last_message = state["messages"][-1]
        has_tool_calls = (
            hasattr(last_message, "tool_calls") and last_message.tool_calls
        )
        self.logger.debug(
            f"Routing: has_tool_calls={has_tool_calls}, message_type={type(last_message).__name__}"
        )
        if has_tool_calls:
            self.logger.info(
                f"Model requested {len(last_message.tool_calls)} tool calls"
            )
            return "tools"
        return "end"

    def _call_model(self, state: WorkflowState) -> dict[str, Any]:
        """Call the model with trimmed message history."""
        trimmed_messages = trim_messages(
            state["messages"],
            max_tokens=self._max_tokens,
            strategy="last",
            token_counter=self._token_counter,
            include_system=True,
            allow_partial=False,
            start_on="human",
        )

        # Check if there are any ToolMessages in the conversation
        # If yes, the model should respond conversationally, not with tool JSON
        has_tool_results = any(
            msg.__class__.__name__ == "ToolMessage" for msg in trimmed_messages
        )

        # Escape curly braces in system prompt for LangChain template compatibility
        escaped_system_prompt = self._system_prompt.replace("{", "{{").replace(
            "}", "}}"
        )

        # Add context-aware instruction for JSON mode
        tool_calling_mode = getattr(
            self._chat_model, "tool_calling_mode", "react"
        )
        if has_tool_results and tool_calling_mode == "json":
            # After tool execution, instruct model to respond normally
            escaped_system_prompt += (
                "\n\nIMPORTANT: You have just used a tool and received the result. "
                "Now respond to the user conversationally with your answer. "
                "Do NOT output JSON format anymore."
            )

        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", escaped_system_prompt),
                MessagesPlaceholder(variable_name="messages"),
            ]
        )
        formatted_prompt = prompt.invoke({"messages": trimmed_messages})

        streamed_content: List[str] = []
        last_chunk_message: Optional[BaseMessage] = None
        response_message: Optional[AIMessage] = None

        if hasattr(self._chat_model, "stream"):
            try:
                for chunk in self._chat_model.stream(formatted_prompt):
                    if self._interrupted:
                        break

                    chunk_message = getattr(chunk, "message", chunk)
                    text = getattr(chunk_message, "content", "") or ""

                    # Always capture last chunk (might have tool_calls with no content)
                    last_chunk_message = chunk_message

                    # Skip content processing if empty, but still capture chunk for tool_calls
                    if not text:
                        continue

                    streamed_content.append(text)
                    # DON'T stream to GUI yet - wait until we know if it's a tool call or not
                    # (we'll send the complete response after parsing)

                if streamed_content:
                    additional_kwargs = {}
                    tool_calls = None
                    if last_chunk_message is not None:
                        additional_kwargs = getattr(
                            last_chunk_message, "additional_kwargs", {}
                        )
                        tool_calls = getattr(
                            last_chunk_message, "tool_calls", None
                        )

                    # Parse tool calls from complete streamed response
                    complete_content = "".join(streamed_content)
                    if self._tools and hasattr(
                        self._chat_model, "parse_tool_calls_from_response"
                    ):
                        parsed_tool_calls, cleaned_content = (
                            self._chat_model.parse_tool_calls_from_response(
                                complete_content
                            )
                        )
                        if parsed_tool_calls:
                            self.logger.debug(
                                f"Parsed {len(parsed_tool_calls)} tool calls from response"
                            )
                            tool_calls = parsed_tool_calls
                            complete_content = cleaned_content

                    # Now that we've parsed tool calls, stream the content to GUI
                    # (will be empty if it was a pure tool call, so GUI won't show JSON)
                    if complete_content and self._token_callback:
                        try:
                            self._token_callback(complete_content)
                        except Exception as callback_error:
                            self.logger.error(
                                "Token callback failed: %s",
                                callback_error,
                                exc_info=True,
                            )

                    response_message = AIMessage(
                        content=complete_content,
                        additional_kwargs=additional_kwargs,
                        tool_calls=tool_calls or [],
                    )
                    print(
                        f"[DEBUG WORKFLOW] AIMessage content: {response_message.content[:200]}"
                    )
            except Exception as exc:
                self.logger.error(
                    "Error during streamed model call: %s", exc, exc_info=True
                )
                streamed_content = []
                response_message = None

        if response_message is None:
            response_message = self._chat_model.invoke(formatted_prompt)
            if (
                self._token_callback
                and hasattr(response_message, "content")
                and response_message.content
            ):
                try:
                    self._token_callback(response_message.content)
                except Exception as callback_error:
                    self.logger.error(
                        "Token callback failed: %s",
                        callback_error,
                        exc_info=True,
                    )

        return {"messages": [response_message]}

    def clear_memory(self):
        """Clear the conversation memory/history."""
        self._memory.message_history.clear()
        # Rebuild workflow with fresh memory
        self._build_and_compile_workflow()

    def set_conversation_id(self, conversation_id: int):
        """Set the conversation ID for persistence.

        Args:
            conversation_id: Conversation ID to use for storing messages
        """
        self._conversation_id = conversation_id
        self._thread_id = str(conversation_id)
        self._memory = DatabaseCheckpointSaver(conversation_id)
        self._build_and_compile_workflow()

    def invoke(self, user_input: str) -> dict[str, Any]:
        """Invoke the workflow with user input."""
        input_messages = [HumanMessage(user_input)]
        config = {"configurable": {"thread_id": self._thread_id}}
        return self._compiled_workflow.invoke(
            {"messages": input_messages}, config
        )

    def stream(self, user_input: str):
        """Stream the workflow execution with user input, yielding messages."""
        input_messages = [HumanMessage(user_input)]
        config = {"configurable": {"thread_id": self._thread_id}}

        # Use stream_mode="values" to get updates more frequently
        # This allows interrupt checking to happen more often
        for event in self._compiled_workflow.stream(
            {"messages": input_messages},
            config,
            stream_mode="values",
        ):
            # Check interrupt flag on each event
            if self._interrupted:
                break
            # Yield the entire state for each update
            if "messages" in event and event["messages"]:
                last_message = event["messages"][-1]
                if (
                    isinstance(last_message, AIMessage)
                    and last_message.content
                ):
                    yield last_message

    def update_system_prompt(self, system_prompt: str):
        """Update the system prompt and rebuild the workflow."""
        self._system_prompt = system_prompt
        self._build_and_compile_workflow()

    def update_tools(self, tools: List[Callable]):
        """Update the tools and rebuild the workflow."""
        self._tools = tools
        self._initialize_model()  # Re-bind tools
        self._build_and_compile_workflow()

    def set_token_callback(
        self, callback: Optional[Callable[[str], None]]
    ) -> None:
        """Register a callback for streaming tokens during model execution."""
        self._token_callback = callback

    def set_interrupted(self, value: bool) -> None:
        """Set the interrupted flag to stop generation."""
        self._interrupted = value
        if value:
            self.logger.info("Workflow interrupted flag set")

    def is_interrupted(self) -> bool:
        """Check if generation has been interrupted."""
        return self._interrupted
