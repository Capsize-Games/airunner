"""LangGraph workflow builder.

This module provides a high-level interface for constructing LangGraph
workflows programmatically.
"""

from typing import Dict, List, Callable, Any, Optional
from langgraph.graph import StateGraph, END

from airunner.settings import AIRUNNER_LOG_LEVEL
from airunner.utils.application import get_logger


logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)


class LangGraphBuilder:
    """Build LangGraph workflows from node definitions.

    This class provides a clean API for constructing LangGraph workflows,
    managing nodes, edges, and compilation.

    Example:
        ```python
        builder = LangGraphBuilder(BaseAgentState)
        builder.add_node("perceive", perceive_func)
        builder.add_node("think", think_func)
        builder.add_edge("perceive", "think")
        builder.set_entry_point("perceive")
        app = builder.compile()
        result = app.invoke(initial_state)
        ```
    """

    def __init__(self, state_class: type):
        """Initialize the builder.

        Args:
            state_class: State class (TypedDict) for the workflow
        """
        self.state_class = state_class
        self.workflow = StateGraph(state_class)
        self.nodes: Dict[str, Callable] = {}
        self.edges: List[tuple] = []
        self.conditional_edges: List[Dict[str, Any]] = []
        self.entry_point: Optional[str] = None

    def add_node(self, name: str, func: Callable) -> "LangGraphBuilder":
        """Add a node to the workflow.

        Args:
            name: Unique node identifier
            func: Function that processes state

        Returns:
            Self for method chaining
        """
        if name in self.nodes:
            logger.warning(f"Node '{name}' already exists, overwriting")

        self.nodes[name] = func
        self.workflow.add_node(name, func)
        logger.debug(f"Added node: {name}")
        return self

    def add_edge(self, source: str, target: str) -> "LangGraphBuilder":
        """Add an edge between nodes.

        Args:
            source: Source node name
            target: Target node name (or "END" for terminal)

        Returns:
            Self for method chaining
        """
        self.edges.append((source, target))

        if target == "END":
            self.workflow.add_edge(source, END)
        else:
            self.workflow.add_edge(source, target)

        logger.debug(f"Added edge: {source} -> {target}")
        return self

    def add_conditional_edge(
        self,
        source: str,
        condition: Callable[[Any], str],
        mapping: Dict[str, str],
    ) -> "LangGraphBuilder":
        """Add conditional routing.

        Args:
            source: Source node name
            condition: Function that returns next node name based on state
            mapping: Map of condition results to target node names

        Returns:
            Self for method chaining
        """
        self.conditional_edges.append(
            {
                "source": source,
                "condition": condition,
                "mapping": mapping,
            }
        )

        # Map "END" string to END constant
        processed_mapping = {}
        for key, value in mapping.items():
            processed_mapping[key] = END if value == "END" else value

        self.workflow.add_conditional_edges(
            source, condition, processed_mapping
        )

        logger.debug(
            f"Added conditional edge: {source} with {len(mapping)} branches"
        )
        return self

    def set_entry_point(self, node_name: str) -> "LangGraphBuilder":
        """Set the entry point for the workflow.

        Args:
            node_name: Name of the node to start execution

        Returns:
            Self for method chaining
        """
        self.entry_point = node_name
        self.workflow.set_entry_point(node_name)
        logger.debug(f"Set entry point: {node_name}")
        return self

    def compile(self, checkpointer=None) -> Any:
        """Compile the workflow.

        Args:
            checkpointer: Optional checkpointer for state persistence

        Returns:
            Compiled LangGraph application

        Raises:
            ValueError: If workflow is invalid
        """
        if not self.entry_point:
            raise ValueError("Entry point must be set before compiling")

        if not self.nodes:
            raise ValueError("At least one node must be added")

        logger.info(
            f"Compiling workflow with {len(self.nodes)} nodes, "
            f"{len(self.edges)} edges, "
            f"{len(self.conditional_edges)} conditional edges"
        )

        compiled = self.workflow.compile(checkpointer=checkpointer)
        return compiled

    def validate(self) -> bool:
        """Validate the workflow structure.

        Returns:
            True if valid, False otherwise
        """
        issues = []

        # Check entry point
        if not self.entry_point:
            issues.append("No entry point set")
        elif self.entry_point not in self.nodes:
            issues.append(f"Entry point '{self.entry_point}' not in nodes")

        # Check that all edge sources/targets exist
        for source, target in self.edges:
            if source not in self.nodes:
                issues.append(f"Edge source '{source}' not found")
            if target != "END" and target not in self.nodes:
                issues.append(f"Edge target '{target}' not found")

        # Check conditional edges
        for edge in self.conditional_edges:
            source = edge["source"]
            if source not in self.nodes:
                issues.append(f"Conditional edge source '{source}' not found")

        if issues:
            logger.error(f"Workflow validation failed: {issues}")
            return False

        logger.info("Workflow validation passed")
        return True

    def get_graph_info(self) -> Dict[str, Any]:
        """Get information about the graph structure.

        Returns:
            Dict with graph statistics and structure
        """
        return {
            "state_class": self.state_class.__name__,
            "entry_point": self.entry_point,
            "num_nodes": len(self.nodes),
            "num_edges": len(self.edges),
            "num_conditional_edges": len(self.conditional_edges),
            "nodes": list(self.nodes.keys()),
            "edges": self.edges,
        }
