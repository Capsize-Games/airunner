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

        self._initialize_model()
        self._build_and_compile_workflow()

    def _initialize_model(self):
        """Bind tools to the chat model if provided."""
        if self._tools and hasattr(self._chat_model, "bind_tools"):
            try:
                self._chat_model = self._chat_model.bind_tools(self._tools)
            except Exception as e:
                # Some models might not support tool binding
                # In that case, tools will be handled differently
                pass

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
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
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

        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", self._system_prompt),
                MessagesPlaceholder(variable_name="messages"),
            ]
        )
        formatted_prompt = prompt.invoke({"messages": trimmed_messages})
        response = self._chat_model.invoke(formatted_prompt)

        return {"messages": [response]}

    def update_system_prompt(self, system_prompt: str):
        """Update the system prompt for the workflow.

        Args:
            system_prompt: New system prompt to use
        """
        self._system_prompt = system_prompt

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
        """Stream the workflow execution with user input."""
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
