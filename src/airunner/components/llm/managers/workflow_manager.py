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
        """Bind tools to the chat model if provided."""
        # Skip tool binding if no tools provided
        if not self._tools or len(self._tools) == 0:
            self.logger.info("No tools provided - skipping tool binding")
            return

        if hasattr(self._chat_model, "bind_tools"):
            try:
                self._chat_model = self._chat_model.bind_tools(self._tools)
                self.logger.info(
                    f"Successfully bound {len(self._tools)} tools to chat model"
                )

                # Add tool schemas to system prompt for local models
                if hasattr(self._chat_model, "get_tool_schemas_text"):
                    tool_schemas = self._chat_model.get_tool_schemas_text()
                    if tool_schemas:
                        self._system_prompt = (
                            f"{self._system_prompt}\n\n{tool_schemas}"
                        )
                        self.logger.info("Added tool schemas to system prompt")

            except NotImplementedError:
                self.logger.warning(
                    f"Local HuggingFace models don't support native function calling. "
                    f"Using prompt-based tool calling instead."
                )
                # Still add tool schemas to system prompt for prompt-based calling
                if hasattr(self._chat_model, "get_tool_schemas_text"):
                    tool_schemas = self._chat_model.get_tool_schemas_text()
                    if tool_schemas:
                        self._system_prompt = (
                            f"{self._system_prompt}\n\n{tool_schemas}"
                        )
                        self.logger.info(
                            "Added tool schemas to system prompt for prompt-based calling"
                        )
            except Exception as e:
                import traceback

                self.logger.warning(
                    f"Could not bind tools to model: {type(e).__name__}: {e}"
                )
                self.logger.debug(f"Full traceback: {traceback.format_exc()}")
        elif self._tools:
            self.logger.warning(
                f"Chat model does not support bind_tools(), {len(self._tools)} tools will not be used"
            )
        else:
            self.logger.debug("No tools to bind")

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

        # Escape curly braces in system prompt for LangChain template compatibility
        escaped_system_prompt = self._system_prompt.replace("{", "{{").replace(
            "}", "}}"
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
                    if not text:
                        continue
                    streamed_content.append(text)
                    last_chunk_message = chunk_message
                    if self._token_callback:
                        try:
                            self._token_callback(text)
                        except Exception as callback_error:
                            self.logger.error(
                                "Token callback failed: %s",
                                callback_error,
                                exc_info=True,
                            )

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
                        self._chat_model, "_parse_tool_calls"
                    ):
                        parsed_tool_calls, cleaned_content = (
                            self._chat_model._parse_tool_calls(
                                complete_content
                            )
                        )
                        if parsed_tool_calls:
                            tool_calls = parsed_tool_calls
                            complete_content = cleaned_content

                    response_message = AIMessage(
                        content=complete_content,
                        additional_kwargs=additional_kwargs,
                        tool_calls=tool_calls or [],
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

        for event in self._compiled_workflow.stream(
            {"messages": input_messages},
            config,
            stream_mode="messages",
        ):
            message = event[0]
            if isinstance(message, AIMessage) and message.content:
                yield message

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
