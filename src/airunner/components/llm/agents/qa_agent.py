"""
QA Agent - Specialized subgraph for question answering tasks.

This agent handles:
- Answering direct questions
- Fact checking
- Providing explanations
- Answer verification
- Confidence scoring
"""

from typing import Any, Annotated, List, Callable
from typing_extensions import TypedDict

from langchain_core.messages import BaseMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langgraph.graph import START, END, StateGraph, add_messages
from langgraph.prebuilt import ToolNode

from airunner.components.llm.core.tool_registry import (
    ToolRegistry,
    ToolCategory,
)
from airunner.settings import AIRUNNER_LOG_LEVEL
from airunner.utils.application import get_logger

logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)


class QAState(TypedDict):
    """
    State schema for QA agent.

    Attributes:
        messages: Conversation messages
        question_type: Type of question (factual, explanation, etc.)
        requires_verification: Whether answer needs fact checking
        confidence_threshold: Minimum confidence for answer
    """

    messages: Annotated[list[BaseMessage], add_messages]
    question_type: str
    requires_verification: bool
    confidence_threshold: float


class QAAgent:
    """
    QA Agent for question answering tasks.

    Uses QA-category tools to help with:
    - Answer verification
    - Confidence scoring
    - Context extraction
    - Clarifying questions
    - Answer ranking
    - Question type identification
    """

    def __init__(
        self,
        chat_model: Any,
        system_prompt: str = None,
    ):
        """
        Initialize QA Agent.

        Args:
            chat_model: LangChain chat model
            system_prompt: Optional custom system prompt
        """
        self._chat_model = chat_model
        self._system_prompt = system_prompt or self._default_system_prompt()
        self._tools = self._get_qa_tools()

        # Bind tools to model
        if self._tools and hasattr(self._chat_model, "bind_tools"):
            self._chat_model = self._chat_model.bind_tools(self._tools)
            logger.info(f"QA agent bound {len(self._tools)} tools")

    def _default_system_prompt(self) -> str:
        """Get default system prompt for QA mode."""
        return """You are a question-answering assistant specializing in:

- Providing accurate, factual answers
- Fact checking and verification
- Explaining concepts clearly
- Identifying when more information is needed
- Assessing answer confidence

Focus on accuracy and clarity. Use your tools to:
- Verify answers against available context
- Score confidence in your answers
- Extract relevant information from context
- Generate clarifying questions when needed
- Rank multiple answer candidates
- Identify the type of question being asked

Always be honest about uncertainty and ask for clarification when needed."""

    def _get_qa_tools(self) -> List[Callable]:
        """Get QA-category tools from registry."""
        qa_tools = ToolRegistry.get_by_category(ToolCategory.QA)
        logger.info(f"Retrieved {len(qa_tools)} QA tools")

        # Convert ToolInfo to actual callable functions
        tools = [tool.func for tool in qa_tools]
        return tools

    def _analyze_question(self, state: QAState) -> dict:
        """
        Analyze the question to determine type and requirements.

        Args:
            state: Current QA state

        Returns:
            Updated state with question_type, verification needs, threshold
        """
        messages = state.get("messages", [])
        if not messages:
            return {
                "question_type": "general",
                "requires_verification": False,
                "confidence_threshold": 0.7,
            }

        # Get last user message
        last_msg = None
        for msg in reversed(messages):
            if hasattr(msg, "type") and msg.type == "human":
                last_msg = msg
                break

        if not last_msg:
            return {
                "question_type": "general",
                "requires_verification": False,
                "confidence_threshold": 0.7,
            }

        content = str(last_msg.content).lower()

        # Detect question type
        question_type = "general"
        if any(word in content for word in ["what", "which"]):
            question_type = "factual"
        elif any(word in content for word in ["why", "how"]):
            question_type = "explanation"
        elif any(word in content for word in ["when", "where"]):
            question_type = "temporal_spatial"
        elif any(word in content for word in ["who"]):
            question_type = "person"
        elif any(
            word in content
            for word in ["is it true", "verify", "check", "confirm"]
        ):
            question_type = "verification"

        # Determine if verification is needed
        requires_verification = question_type in [
            "factual",
            "verification",
            "temporal_spatial",
        ]

        # Set confidence threshold based on question type
        confidence_threshold = 0.7  # default
        if question_type == "verification":
            confidence_threshold = 0.9  # High confidence needed
        elif question_type == "explanation":
            confidence_threshold = 0.6  # Explanations can be more flexible

        logger.info(
            f"Question analysis: type={question_type}, "
            f"verify={requires_verification}, threshold={confidence_threshold}"
        )

        return {
            "question_type": question_type,
            "requires_verification": requires_verification,
            "confidence_threshold": confidence_threshold,
        }

    def _call_model(self, state: QAState) -> dict:
        """
        Call the LLM with QA-specific context.

        Args:
            state: Current QA state

        Returns:
            Updated state with new AI message
        """
        messages = state.get("messages", [])
        question_type = state.get("question_type", "general")
        requires_verification = state.get("requires_verification", False)
        confidence_threshold = state.get("confidence_threshold", 0.7)

        # Build prompt with QA context
        verification_note = (
            " (requires verification)" if requires_verification else ""
        )

        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", self._system_prompt),
                (
                    "system",
                    f"Question type: {question_type}{verification_note}. "
                    f"Minimum confidence: {confidence_threshold:.0%}",
                ),
                MessagesPlaceholder(variable_name="messages"),
            ]
        )

        chain = prompt | self._chat_model
        response = chain.invoke({"messages": messages})

        return {"messages": [response]}

    def _route_after_model(self, state: QAState) -> str:
        """
        Determine next step after model call.

        Args:
            state: Current QA state

        Returns:
            Next node name ("tools" or "end")
        """
        messages = state.get("messages", [])
        if not messages:
            return "end"

        last_message = messages[-1]

        # Check if model wants to use tools
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            logger.info(
                f"Model requested {len(last_message.tool_calls)} tool calls"
            )
            return "tools"

        return "end"

    def build_graph(self) -> StateGraph:
        """
        Build the QA agent graph.

        Returns:
            StateGraph for QA mode
        """
        logger.info("Building QA agent graph")

        graph = StateGraph(QAState)

        # Add nodes
        graph.add_node("analyze_question", self._analyze_question)
        graph.add_node("model", self._call_model)

        if self._tools:
            tool_node = ToolNode(self._tools)
            graph.add_node("tools", tool_node)

        # Add edges
        graph.add_edge(START, "analyze_question")
        graph.add_edge("analyze_question", "model")

        if self._tools:
            graph.add_conditional_edges(
                "model",
                self._route_after_model,
                {
                    "tools": "tools",
                    "end": END,
                },
            )
            graph.add_edge("tools", "model")
        else:
            graph.add_edge("model", END)

        logger.info("QA agent graph built successfully")
        return graph

    def compile(self) -> Any:
        """
        Build and compile the QA agent graph.

        Returns:
            Compiled graph ready for invocation
        """
        graph = self.build_graph()
        compiled = graph.compile()
        logger.info("QA agent compiled successfully")
        return compiled
