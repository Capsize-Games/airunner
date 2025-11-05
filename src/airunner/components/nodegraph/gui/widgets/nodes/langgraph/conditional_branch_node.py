"""Conditional Branch Node for routing in LangGraph workflows.

This node creates conditional routing based on state.
"""

from typing import Dict
from airunner.vendor.nodegraphqt.constants import NodePropWidgetEnum
from airunner.components.nodegraph.gui.widgets.nodes.langgraph.base_langgraph_node import (
    BaseLangGraphNode,
)


class ConditionalBranchNode(BaseLangGraphNode):
    """Conditional routing node.

    This node evaluates a condition and routes to different
    nodes based on the result.
    """

    NODE_NAME = "Conditional Branch"
    is_conditional = True

    # Conditional nodes have multiple output exec ports
    has_exec_out_port = False  # We'll add custom ones

    _input_ports = [
        dict(name="condition_value", display_name="Condition Value"),
    ]

    _output_ports = [
        dict(name="true_output", display_name="True"),
        dict(name="false_output", display_name="False"),
    ]

    _properties = [
        dict(
            name="condition_code",
            value='return state.get("next_action") == "continue"',
            widget_type=NodePropWidgetEnum.QTEXT_EDIT,
            tab="condition",
        ),
        dict(
            name="true_route",
            value="continue",
            widget_type=NodePropWidgetEnum.QLINE_EDIT,
            tab="routing",
        ),
        dict(
            name="false_route",
            value="END",
            widget_type=NodePropWidgetEnum.QLINE_EDIT,
            tab="routing",
        ),
    ]

    def __init__(self):
        """Initialize conditional branch node."""
        super().__init__()
        # Add execution output ports for true/false branches
        self.add_output(
            "exec_out_true",
            multi_output=False,
            display_name="True",
            color=(0, 255, 0),
            painter_func=self._draw_exec_port,
        )
        self.add_output(
            "exec_out_false",
            multi_output=False,
            display_name="False",
            color=(255, 0, 0),
            painter_func=self._draw_exec_port,
        )

    def get_node_type(self) -> str:
        """Get node type identifier."""
        return "conditional"

    def get_description(self) -> str:
        """Get node description."""
        return "Conditional routing"

    def to_langgraph_code(self) -> str:
        """Generate Python code for conditional routing.

        Returns:
            Python code string
        """
        condition_code = self.get_property("condition_code")
        true_route = self.get_property("true_route")
        false_route = self.get_property("false_route")

        func_name = self._sanitize_name(self.name())

        code = f'''def {func_name}_condition(state: AgentState) -> str:
    """Conditional routing for {self.name()}"""
    try:
        # Evaluate condition
        {condition_code}
        result = {condition_code}
        
        if result:
            return "{true_route}"
        else:
            return "{false_route}"
    
    except Exception as e:
        logger.error(f"Condition evaluation error: {{e}}")
        return "{false_route}"'''

        return code

    def get_condition_mapping(self) -> Dict[str, str]:
        """Get the routing mapping for this conditional.

        Returns:
            Dict mapping condition results to node names
        """
        true_route = self.get_property("true_route")
        false_route = self.get_property("false_route")

        # Find connected nodes
        true_port = None
        false_port = None

        for port in self.output_ports():
            if "true" in port.name().lower():
                true_port = port
            elif "false" in port.name().lower():
                false_port = port

        mapping = {}

        if true_port and true_port.connected_ports():
            target_node = true_port.connected_ports()[0].node()
            mapping[true_route] = target_node.name()

        if false_port and false_port.connected_ports():
            target_node = false_port.connected_ports()[0].node()
            mapping[false_route] = target_node.name()

        return mapping

    @staticmethod
    def _sanitize_name(name: str) -> str:
        """Sanitize node name to valid Python identifier."""
        sanitized = "".join(
            c if c.isalnum() or c == "_" else "_" for c in name
        )
        if sanitized and sanitized[0].isdigit():
            sanitized = f"node_{sanitized}"
        return sanitized or "condition_node"
