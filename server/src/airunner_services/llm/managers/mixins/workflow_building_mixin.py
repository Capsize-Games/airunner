"""Workflow building mixin for WorkflowManager.

Handles LangGraph workflow construction and compilation.
"""

from typing import Any, Dict, TYPE_CHECKING

from langgraph.graph import START, END, StateGraph

from airunner_services.settings import AIRUNNER_LOG_LEVEL
from airunner_services.utils.application import get_logger

if TYPE_CHECKING:
    pass


class WorkflowBuildingMixin:
    """Manages LangGraph workflow construction and compilation."""

    def __init__(self):
        """Initialize workflow building mixin."""
        self.logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)
        self._workflow = None
        self._compiled_workflow = None
        self._memory = None
        self._tools = []
        self._chat_model = None

    def _build_and_compile_workflow(self):
        """Build and compile the LangGraph workflow."""
        # CRITICAL: Inject WorkflowState into function globals for LangGraph's get_type_hints()
        # This is needed because LangGraph introspects type hints at runtime
        from airunner_services.llm.workflow_manager import (
            WorkflowState,
        )

        self._route_after_model.__func__.__globals__["WorkflowState"] = (
            WorkflowState
        )

        self.logger.info("Building standard workflow")
        self._workflow = self._build_graph()
        self._compiled_workflow = self._workflow.compile(
            checkpointer=self._memory
        )

    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow.

        Returns:
            Constructed StateGraph
        """
        from airunner_services.llm.workflow_manager import (
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

    def _route_after_force_response(self, state: Dict[str, Any]) -> str:
        """Route after force_response node.

        For workflow continuation (duplicate workflow tool detected),
        route back to the model so it can call the next tool.
        Otherwise, end the graph.

        Args:
            state: Current workflow state

        Returns:
            "model" for workflow continuation, "end" otherwise
        """
        if state.get("workflow_continuation"):
            self.logger.info(
                "Routing from force_response back to model for workflow continuation"
            )
            return "model"
        return "end"

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
        # After tools execute, conditionally route:
        # - "model" if tool returned data needing interpretation
        # - "force_response" if tool is RAG/search and should synthesize results directly
        # - "end" if tool was status-only (like update_mood)
        workflow.add_conditional_edges(
            "tools",
            self._route_after_tools,
            {
                "model": "model",
                "force_response": "force_response",
                "end": END,
            },
        )
        # After force_response, conditionally route:
        # - "model" for workflow continuation (duplicate workflow tool detected)
        # - "end" for normal forced responses
        workflow.add_conditional_edges(
            "force_response",
            self._route_after_force_response,
            {
                "model": "model",
                "end": END,
            },
        )
