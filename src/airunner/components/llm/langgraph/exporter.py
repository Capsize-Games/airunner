"""Export NodeGraph to executable LangGraph Python code.

This module provides the bridge between the visual NodeGraph interface
and executable LangGraph workflows.
"""

from typing import Dict, Any, Optional
from pathlib import Path
from airunner.components.nodegraph.gui.widgets.custom_node_graph import (
    CustomNodeGraph,
)
from airunner.components.llm.langgraph.code_generator import (
    LangGraphCodeGenerator,
)
from airunner.settings import AIRUNNER_LOG_LEVEL
from airunner.utils.application import get_logger


logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)


class LangGraphExporter:
    """Export NodeGraph to executable LangGraph Python code.

    This class analyzes a visual NodeGraph and generates clean,
    executable Python code that implements the same workflow using
    LangGraph.
    """

    def __init__(self):
        """Initialize the exporter."""
        self.generator = None

    def export(
        self,
        graph: CustomNodeGraph,
        output_path: Optional[Path] = None,
        workflow_name: str = "agent_workflow",
    ) -> str:
        """Export graph to Python code.

        Args:
            graph: NodeGraph instance
            output_path: Optional path to save generated code
            workflow_name: Name for the workflow

        Returns:
            Generated Python code

        Raises:
            ValueError: If graph is invalid
        """
        logger.info(f"Exporting workflow: {workflow_name}")

        # Analyze graph structure
        analysis = self._analyze_graph(graph)

        # Validate
        if not self._validate_graph(analysis):
            raise ValueError("Graph validation failed")

        # Initialize code generator
        state_schema_node = analysis.get("state_schema_node")
        if state_schema_node:
            state_class_name = state_schema_node.get_state_class_name()
        else:
            state_class_name = "AgentState"

        self.generator = LangGraphCodeGenerator(
            workflow_name=workflow_name,
            state_class_name=state_class_name,
        )

        # Generate code
        code = self.generator.generate(
            nodes=analysis["nodes"],
            edges=analysis["edges"],
            conditional_edges=analysis["conditional_edges"],
            state_fields=analysis["state_fields"],
            entry_point=analysis["entry_point"],
        )

        # Format code
        code = self.generator.format_code(code)

        # Save if requested
        if output_path:
            self.generator.save(code, output_path)

        logger.info("Workflow export completed")
        return code

    def _analyze_graph(self, graph: CustomNodeGraph) -> Dict[str, Any]:
        """Analyze graph structure.

        Args:
            graph: NodeGraph instance

        Returns:
            Dict with graph analysis
        """
        from airunner.components.nodegraph.gui.widgets.nodes.langgraph.base_langgraph_node import (
            BaseLangGraphNode,
        )
        from airunner.components.nodegraph.gui.widgets.nodes.langgraph.state_schema_node import (
            StateSchemaNode,
        )

        nodes = {}
        edges = []
        conditional_edges = []
        state_schema_node = None
        entry_point = None

        # Find all LangGraph nodes
        for node in graph.all_nodes():
            if not isinstance(node, BaseLangGraphNode):
                continue

            # Track state schema node
            if isinstance(node, StateSchemaNode):
                state_schema_node = node
                continue

            # Get node config
            node_config = node.get_node_config()
            nodes[node.name()] = node_config

            # Find entry point (node with no exec input or first node)
            if node.is_entry_node() or not any(
                p.connected_ports()
                for p in node.input_ports()
                if "exec" in p.name().lower()
            ):
                if not entry_point:
                    entry_point = node.name()

            # Analyze edges
            if node.is_conditional:
                # Conditional edges
                condition_config = {
                    "source": node.name(),
                    "condition_code": node.get_property("condition_code"),
                    "mapping": node.get_condition_mapping(),
                }
                conditional_edges.append(condition_config)
            else:
                # Regular edges
                for output_port in node.output_ports():
                    if "exec" not in output_port.name().lower():
                        continue

                    for connected_port in output_port.connected_ports():
                        target_node = connected_port.node()
                        if isinstance(target_node, BaseLangGraphNode):
                            edges.append((node.name(), target_node.name()))

        # Get state fields
        state_fields = {}
        if state_schema_node:
            state_fields = state_schema_node.get_state_fields()
        else:
            # Default state
            state_fields = {
                "messages": "List[str]",
                "next_action": "str",
                "error": "Optional[str]",
                "metadata": "Dict[str, Any]",
            }

        # If no entry point found, use first node
        if not entry_point and nodes:
            entry_point = list(nodes.keys())[0]

        return {
            "nodes": nodes,
            "edges": edges,
            "conditional_edges": conditional_edges,
            "state_fields": state_fields,
            "state_schema_node": state_schema_node,
            "entry_point": entry_point,
        }

    def _validate_graph(self, analysis: Dict[str, Any]) -> bool:
        """Validate graph structure.

        Args:
            analysis: Graph analysis dict

        Returns:
            True if valid, False otherwise
        """
        issues = []

        # Check for nodes
        if not analysis["nodes"]:
            issues.append("No LangGraph nodes found in graph")

        # Check for entry point
        if not analysis["entry_point"]:
            issues.append("No entry point found")

        # Check for disconnected nodes
        connected_nodes = set()
        connected_nodes.add(analysis["entry_point"])

        for source, target in analysis["edges"]:
            connected_nodes.add(source)
            connected_nodes.add(target)

        for edge in analysis["conditional_edges"]:
            connected_nodes.add(edge["source"])
            for target in edge["mapping"].values():
                if target != "END":
                    connected_nodes.add(target)

        disconnected = set(analysis["nodes"].keys()) - connected_nodes
        if disconnected:
            issues.append(f"Disconnected nodes: {disconnected}")

        if issues:
            for issue in issues:
                logger.error(f"Validation error: {issue}")
            return False

        return True

    def get_graph_info(self, graph: CustomNodeGraph) -> Dict[str, Any]:
        """Get information about a graph without exporting.

        Args:
            graph: NodeGraph instance

        Returns:
            Dict with graph info
        """
        analysis = self._analyze_graph(graph)
        return {
            "num_nodes": len(analysis["nodes"]),
            "num_edges": len(analysis["edges"]),
            "num_conditional_edges": len(analysis["conditional_edges"]),
            "entry_point": analysis["entry_point"],
            "state_fields": list(analysis["state_fields"].keys()),
            "node_names": list(analysis["nodes"].keys()),
        }
