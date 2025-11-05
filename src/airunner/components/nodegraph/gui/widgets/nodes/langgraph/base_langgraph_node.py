"""Base class for all LangGraph visual nodes.

This module provides the base node class that all LangGraph nodes inherit from,
providing common functionality for code generation and validation.
"""

from typing import Dict, Any, List
from airunner.components.nodegraph.gui.widgets.nodes.core.base_workflow_node import (
    BaseWorkflowNode,
)


class BaseLangGraphNode(BaseWorkflowNode):
    """Base class for all LangGraph nodes.

    This class extends BaseWorkflowNode to add LangGraph-specific
    functionality like code generation and state management.

    Attributes:
        __identifier__: Namespace identifier for the node
        state_key: Key in state dict this node modifies
        is_conditional: Does this create a branch?
        is_loop: Does this create a cycle?
        node_color: Visual color for the node (LangGraph nodes are blue-ish)
    """

    __identifier__ = "airunner.langgraph"

    # LangGraph-specific attributes
    state_key: str = ""
    is_conditional: bool = False
    is_loop: bool = False

    # Visual styling for LangGraph nodes
    node_color = (100, 150, 255)  # Blue color to distinguish from other nodes

    def __init__(self):
        """Initialize LangGraph node."""
        super().__init__()

    def to_langgraph_code(self) -> str:
        """Generate LangGraph Python code for this node.

        This method must be implemented by subclasses to generate
        the appropriate Python code for their functionality.

        Returns:
            Python code string

        Raises:
            NotImplementedError: If subclass doesn't implement
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement to_langgraph_code"
        )

    def get_node_config(self) -> Dict[str, Any]:
        """Get node configuration for code generation.

        Returns:
            Dict with node configuration
        """
        return {
            "name": self.name(),
            "type": self.get_node_type(),
            "description": self.get_description(),
            "properties": self.get_all_properties(),
            "state_key": self.state_key,
            "is_conditional": self.is_conditional,
            "is_loop": self.is_loop,
        }

    def get_node_type(self) -> str:
        """Get the node type identifier.

        Returns:
            Node type string (override in subclasses)
        """
        return "custom"

    def get_description(self) -> str:
        """Get node description for generated code.

        Returns:
            Description string
        """
        return f"{self.NODE_NAME} node"

    def get_all_properties(self) -> Dict[str, Any]:
        """Get all node properties as a dict.

        Returns:
            Dict of property_name: value
        """
        properties = {}
        for prop_name in self.properties.keys():
            try:
                properties[prop_name] = self.get_property(prop_name)
            except Exception:
                continue
        return properties

    def validate_connections(self) -> tuple[bool, str]:
        """Validate node connections are valid for LangGraph.

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check execution ports
        if self.has_exec_in_port:
            exec_in_ports = [
                p
                for p in self.input_ports()
                if p.name() == self.EXEC_IN_PORT_NAME
            ]
            if exec_in_ports:
                exec_in = exec_in_ports[0]
                if not exec_in.connected_ports():
                    # Entry node doesn't need input connection
                    if not self.is_entry_node():
                        return False, "Execution input must be connected"

        # Conditional nodes must have multiple outputs
        if self.is_conditional:
            exec_out_ports = [
                p
                for p in self.output_ports()
                if p.name() == self.EXEC_OUT_PORT_NAME
            ]
            if len(exec_out_ports) < 2:
                return (
                    False,
                    "Conditional nodes must have at least 2 output paths",
                )

        return True, ""

    def is_entry_node(self) -> bool:
        """Check if this is an entry node (no exec input needed).

        Returns:
            True if entry node, False otherwise
        """
        return False

    def get_state_requirements(self) -> Dict[str, type]:
        """Get required state fields for this node.

        Returns:
            Dict of field_name: type
        """
        return {}

    def get_input_state_keys(self) -> List[str]:
        """Get state keys this node reads from.

        Returns:
            List of state field names
        """
        return []

    def get_output_state_keys(self) -> List[str]:
        """Get state keys this node writes to.

        Returns:
            List of state field names
        """
        if self.state_key:
            return [self.state_key]
        return []

    def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute node (for runtime workflow execution).

        Args:
            input_data: Input data from previous nodes

        Returns:
            Output data for next nodes
        """
        # LangGraph nodes are executed via generated code,
        # not through this method
        return input_data

    def get_next_node(self, state: Dict[str, Any]) -> str:
        """Get next node name based on state (for conditional nodes).

        Args:
            state: Current workflow state

        Returns:
            Name of next node to execute
        """
        # Default: follow first output connection
        exec_out_ports = [
            p
            for p in self.output_ports()
            if p.name() == self.EXEC_OUT_PORT_NAME
        ]
        if exec_out_ports and exec_out_ports[0].connected_ports():
            next_port = exec_out_ports[0].connected_ports()[0]
            return next_port.node().name()

        return "END"
