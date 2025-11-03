"""Workflow building mixin for WorkflowManager.

Handles LangGraph workflow construction and compilation.
"""

import logging
from typing import TYPE_CHECKING

from langgraph.graph import START, END, StateGraph

if TYPE_CHECKING:
    from airunner.components.llm.managers.workflow_manager import WorkflowState


class WorkflowBuildingMixin:
    """Manages LangGraph workflow construction and compilation."""

    def __init__(self):
        """Initialize workflow building mixin."""
        self.logger = logging.getLogger(__name__)
        self._workflow = None
        self._compiled_workflow = None
        self._use_mode_routing = False
        self._memory = None
        self._tools = []
        self._chat_model = None

    def _build_and_compile_workflow(self):
        """Build and compile the LangGraph workflow."""
        if self._use_mode_routing:
            self.logger.info("Building workflow with mode-based routing")
            self._build_mode_based_workflow()
        else:
            self.logger.info("Building standard workflow")
            self._workflow = self._build_graph()
            self._compiled_workflow = self._workflow.compile(
                checkpointer=self._memory
            )

    def _build_mode_based_workflow(self):
        """Build workflow using parent routing graph with specialized subgraphs."""
        from airunner.components.llm.managers.parent_graph_builder import (
            ParentGraphBuilder,
        )
        from airunner.components.llm.agents import (
            AuthorAgent,
            CodeAgent,
            ResearchAgent,
            QAAgent,
        )

        self.logger.info("Building specialized agent subgraphs")

        # Build specialized subgraphs
        author_subgraph = self._build_author_subgraph()
        code_subgraph = self._build_code_subgraph()
        research_subgraph = self._build_research_subgraph()
        qa_subgraph = self._build_qa_subgraph()
        general_subgraph = self._build_general_subgraph()

        self.logger.info(
            "All subgraphs built successfully - "
            "author, code, research, qa, general"
        )

        # Build parent routing graph
        self._compiled_workflow = self._build_parent_graph(
            author_subgraph,
            code_subgraph,
            research_subgraph,
            qa_subgraph,
            general_subgraph,
        )

        self.logger.info("Mode-based routing workflow compiled successfully")

    def _build_author_subgraph(self):
        """Build author agent subgraph.

        Returns:
            Compiled author subgraph
        """
        from airunner.components.llm.agents import AuthorAgent

        return AuthorAgent(chat_model=self._chat_model).compile()

    def _build_code_subgraph(self):
        """Build code agent subgraph.

        Returns:
            Compiled code subgraph
        """
        from airunner.components.llm.agents import CodeAgent

        return CodeAgent(chat_model=self._chat_model).compile()

    def _build_research_subgraph(self):
        """Build research agent subgraph.

        Returns:
            Compiled research subgraph
        """
        from airunner.components.llm.agents import ResearchAgent

        return ResearchAgent(chat_model=self._chat_model).compile()

    def _build_qa_subgraph(self):
        """Build QA agent subgraph.

        Returns:
            Compiled QA subgraph
        """
        from airunner.components.llm.agents import QAAgent

        return QAAgent(chat_model=self._chat_model).compile()

    def _build_general_subgraph(self):
        """Build general/fallback subgraph.

        Returns:
            Compiled general subgraph
        """
        return self._build_graph().compile()

    def _build_parent_graph(
        self,
        author_subgraph,
        code_subgraph,
        research_subgraph,
        qa_subgraph,
        general_subgraph,
    ):
        """Build parent routing graph from subgraphs.

        Args:
            author_subgraph: Compiled author agent graph
            code_subgraph: Compiled code agent graph
            research_subgraph: Compiled research agent graph
            qa_subgraph: Compiled QA agent graph
            general_subgraph: Compiled general agent graph

        Returns:
            Compiled parent routing graph
        """
        from airunner.components.llm.managers.parent_graph_builder import (
            ParentGraphBuilder,
        )

        builder = ParentGraphBuilder(
            chat_model=self._chat_model,
            author_graph=author_subgraph,
            code_graph=code_subgraph,
            research_graph=research_subgraph,
            qa_graph=qa_subgraph,
            general_graph=general_subgraph,
        )

        return builder.compile()

    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow.

        Returns:
            Constructed StateGraph
        """
        from airunner.components.llm.managers.workflow_manager import (
            WorkflowState,
        )

        workflow = StateGraph(WorkflowState)

        # Add nodes
        workflow.add_node("model", self._call_model)
        workflow.add_node("force_response", self._force_response_node)
        if self._tools:
            # Use custom tool node that emits status signals
            workflow.add_node("tools", self._execute_tools_with_status)

        # Add edges
        workflow.add_edge(START, "model")

        if self._tools:
            self._add_tool_workflow_edges(workflow)
        else:
            workflow.add_edge("model", END)

        return workflow

    def _add_tool_workflow_edges(self, workflow: StateGraph):
        """Add edges for tool-enabled workflow.

        Args:
            workflow: StateGraph to add edges to
        """
        workflow.add_conditional_edges(
            "model",
            self._route_after_model,
            {
                "tools": "tools",
                "force_response": "force_response",
                "end": END,
            },
        )
        workflow.add_edge("tools", "model")
        workflow.add_edge("force_response", END)
