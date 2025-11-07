"""
Parent graph builder for mode-based routing architecture.

This module builds the top-level StateGraph that routes user queries
to specialized subgraphs based on intent classification.
"""

from typing import Any, Optional, Annotated
from typing_extensions import TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph import START, END, StateGraph, add_messages

from airunner.components.llm.managers.mode_router import (
    UserIntent,
    intent_classifier_node,
    route_by_intent,
)
from airunner.settings import AIRUNNER_LOG_LEVEL
from airunner.utils.application import get_logger

logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)


class ParentState(TypedDict):
    """
    Parent graph state schema.

    Attributes:
        messages: Conversation messages (managed by add_messages)
        intent: Classified user intent (mode, confidence, reasoning)
        subgraph_result: Result from specialized subgraph
    """

    messages: Annotated[list[BaseMessage], add_messages]
    intent: Optional[UserIntent]
    subgraph_result: Optional[dict]


class ParentGraphBuilder:
    """
    Builds the parent routing graph.

    The parent graph:
    1. Classifies user intent
    2. Routes to specialized subgraph (author/code/research/qa/general)
    3. Compiles final response
    """

    def __init__(
        self,
        chat_model: Any,
        author_graph: Optional[Any] = None,
        code_graph: Optional[Any] = None,
        research_graph: Optional[Any] = None,
        qa_graph: Optional[Any] = None,
        general_graph: Optional[Any] = None,
    ):
        """
        Initialize parent graph builder.

        Args:
            chat_model: LangChain chat model for intent classification
            author_graph: Compiled author subgraph (optional)
            code_graph: Compiled code subgraph (optional)
            research_graph: Compiled research subgraph (optional)
            qa_graph: Compiled QA subgraph (optional)
            general_graph: Compiled general subgraph (optional)
        """
        self._chat_model = chat_model
        self._author_graph = author_graph
        self._code_graph = code_graph
        self._research_graph = research_graph
        self._qa_graph = qa_graph
        self._general_graph = general_graph

        logger.info(
            f"ParentGraphBuilder initialized with subgraphs: "
            f"author={author_graph is not None}, "
            f"code={code_graph is not None}, "
            f"research={research_graph is not None}, "
            f"qa={qa_graph is not None}, "
            f"general={general_graph is not None}"
        )

    def _intent_classifier(self, state: ParentState) -> dict:
        """
        Intent classification node.

        Args:
            state: Current parent state

        Returns:
            Updated state with intent field
        """
        return intent_classifier_node(state, self._chat_model)

    def _author_node(self, state: ParentState) -> dict:
        """
        Author mode subgraph node.

        Args:
            state: Current parent state

        Returns:
            Updated state with subgraph result
        """
        if not self._author_graph:
            logger.warning("Author graph not available, using placeholder")
            return {
                "subgraph_result": {"error": "Author mode not implemented"}
            }

        logger.info("Invoking author subgraph")
        result = self._author_graph.invoke(state)
        return {"subgraph_result": result}

    def _code_node(self, state: ParentState) -> dict:
        """
        Code mode subgraph node.

        Args:
            state: Current parent state

        Returns:
            Updated state with subgraph result
        """
        if not self._code_graph:
            logger.warning("Code graph not available, using placeholder")
            return {"subgraph_result": {"error": "Code mode not implemented"}}

        logger.info("Invoking code subgraph")
        result = self._code_graph.invoke(state)
        return {"subgraph_result": result}

    def _research_node(self, state: ParentState) -> dict:
        """
        Research mode subgraph node.

        Args:
            state: Current parent state

        Returns:
            Updated state with subgraph result
        """
        if not self._research_graph:
            logger.warning("Research graph not available, using placeholder")
            return {
                "subgraph_result": {"error": "Research mode not implemented"}
            }

        logger.info("Invoking research subgraph")
        result = self._research_graph.invoke(state)
        return {"subgraph_result": result}

    def _qa_node(self, state: ParentState) -> dict:
        """
        QA mode subgraph node.

        Args:
            state: Current parent state

        Returns:
            Updated state with subgraph result
        """
        if not self._qa_graph:
            logger.warning("QA graph not available, using placeholder")
            return {"subgraph_result": {"error": "QA mode not implemented"}}

        logger.info("Invoking QA subgraph")
        result = self._qa_graph.invoke(state)
        return {"subgraph_result": result}

    def _general_node(self, state: ParentState) -> dict:
        """
        General mode subgraph node (fallback).

        Args:
            state: Current parent state

        Returns:
            Updated state with subgraph result
        """
        if not self._general_graph:
            logger.warning("General graph not available, using placeholder")
            return {
                "subgraph_result": {"error": "General mode not implemented"}
            }

        logger.info("Invoking general subgraph")
        result = self._general_graph.invoke(state)
        return {"subgraph_result": result}

    def _compile_response(self, state: ParentState) -> dict:
        """
        Compile final response from subgraph result.

        Args:
            state: Current parent state with subgraph result

        Returns:
            Updated state with final messages
        """
        subgraph_result = state.get("subgraph_result")
        if not subgraph_result:
            logger.warning("No subgraph result, returning empty response")
            return {}

        # Extract messages from subgraph result
        result_messages = subgraph_result.get("messages", [])

        logger.info(f"Compiled response with {len(result_messages)} messages")

        # Messages are automatically merged via add_messages reducer
        return {"messages": result_messages}

    def build(self) -> StateGraph:
        """
        Build and return the parent routing graph.

        Returns:
            Compiled StateGraph ready for invocation
        """
        logger.info("Building parent routing graph")

        # Create graph
        graph = StateGraph(ParentState)

        # Add nodes
        graph.add_node("classify_intent", self._intent_classifier)
        graph.add_node("author", self._author_node)
        graph.add_node("code", self._code_node)
        graph.add_node("research", self._research_node)
        graph.add_node("qa", self._qa_node)
        graph.add_node("general", self._general_node)
        graph.add_node("compile_response", self._compile_response)

        # Add edges
        graph.add_edge(START, "classify_intent")

        # Conditional routing based on intent
        graph.add_conditional_edges(
            "classify_intent",
            route_by_intent,
            {
                "author": "author",
                "code": "code",
                "research": "research",
                "qa": "qa",
                "general": "general",
            },
        )

        # All subgraphs lead to compile_response
        graph.add_edge("author", "compile_response")
        graph.add_edge("code", "compile_response")
        graph.add_edge("research", "compile_response")
        graph.add_edge("qa", "compile_response")
        graph.add_edge("general", "compile_response")

        # Final edge
        graph.add_edge("compile_response", END)

        logger.info("Parent graph built successfully")
        return graph

    def compile(self) -> Any:
        """
        Build and compile the parent graph.

        Returns:
            Compiled graph ready for invocation
        """
        graph = self.build()
        compiled = graph.compile()
        logger.info("Parent graph compiled successfully")
        return compiled
