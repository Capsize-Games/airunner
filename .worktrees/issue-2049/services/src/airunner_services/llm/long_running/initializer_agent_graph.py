"""Graph-construction helpers for the initializer agent."""

from __future__ import annotations

from typing import Any

from langgraph.graph import END, START, StateGraph

from airunner_services.llm.long_running.initializer_agent_state import (
    InitializerWorkflowState,
)


def build_initializer_graph(agent: Any) -> Any:
    """Build the initializer workflow graph."""
    workflow = StateGraph(InitializerWorkflowState)
    workflow.add_node("analyze_requirements", agent._analyze_requirements)
    workflow.add_node("generate_features", agent._generate_features)
    workflow.add_node("create_project", agent._create_project)
    workflow.add_node("finalize", agent._finalize)
    workflow.add_edge(START, "analyze_requirements")
    workflow.add_edge("analyze_requirements", "generate_features")
    workflow.add_edge("generate_features", "create_project")
    workflow.add_edge("create_project", "finalize")
    workflow.add_edge("finalize", END)
    return workflow.compile()