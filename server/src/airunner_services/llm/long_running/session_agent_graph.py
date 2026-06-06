"""Graph construction helpers for the long-running Session Agent."""

from __future__ import annotations

from typing import Any

from langgraph.graph import END, START, StateGraph

from airunner_services.llm.long_running.session_agent_state import (
    SessionWorkflowState,
)


def _add_nodes(workflow: StateGraph, agent: Any) -> None:
    """Register workflow nodes for the Session Agent."""
    workflow.add_node("orientation", agent._orientation_node)
    workflow.add_node("planning", agent._planning_node)
    workflow.add_node("implementation", agent._implementation_node)
    workflow.add_node("verification", agent._verification_node)
    workflow.add_node("cleanup", agent._cleanup_node)


def _add_edges(workflow: StateGraph, agent: Any) -> None:
    """Register workflow edges for the Session Agent."""
    workflow.add_edge(START, "orientation")
    workflow.add_edge("orientation", "planning")
    workflow.add_conditional_edges(
        "planning",
        agent._route_after_planning,
        {"implement": "implementation", "end": "cleanup"},
    )
    workflow.add_conditional_edges(
        "implementation",
        agent._route_after_implementation,
        {
            "verify": "verification",
            "continue": "implementation",
            "end": "cleanup",
        },
    )
    workflow.add_conditional_edges(
        "verification",
        agent._route_after_verification,
        {"fix": "implementation", "done": "cleanup"},
    )
    workflow.add_edge("cleanup", END)


def build_graph(agent: Any) -> Any:
    """Build the LangGraph workflow for session execution."""
    workflow = StateGraph(SessionWorkflowState)
    _add_nodes(workflow, agent)
    _add_edges(workflow, agent)
    return workflow.compile()
