"""Tool Call Node for executing registered tools.

This node executes tools from the ToolRegistry.
"""

from typing import List
from airunner.vendor.nodegraphqt.constants import NodePropWidgetEnum
from airunner.components.nodegraph.gui.widgets.nodes.langgraph.base_langgraph_node import (
    BaseLangGraphNode,
)


class ToolCallNode(BaseLangGraphNode):
    """Execute a registered tool.

    This node calls a tool from the ToolRegistry and stores
    the result in state.
    """

    NODE_NAME = "Tool Call"
    state_key = "tool_results"

    _input_ports = [
        dict(name="tool_input", display_name="Tool Input"),
    ]

    _output_ports = [
        dict(name="tool_output", display_name="Tool Output"),
    ]

    _properties = [
        dict(
            name="tool_name",
            value="",
            widget_type=NodePropWidgetEnum.QLINE_EDIT,
            tab="tool",
        ),
        dict(
            name="input_key",
            value="tool_input",
            widget_type=NodePropWidgetEnum.QLINE_EDIT,
            tab="state",
        ),
        dict(
            name="output_key",
            value="tool_output",
            widget_type=NodePropWidgetEnum.QLINE_EDIT,
            tab="state",
        ),
    ]

    def get_node_type(self) -> str:
        """Get node type identifier."""
        return "tool"

    def get_description(self) -> str:
        """Get node description."""
        tool_name = self.get_property("tool_name")
        return f"Execute tool: {tool_name}"

    def to_langgraph_code(self) -> str:
        """Generate Python code for tool execution.

        Returns:
            Python code string
        """
        tool_name = self.get_property("tool_name")
        input_key = self.get_property("input_key")
        output_key = self.get_property("output_key")

        func_name = self._sanitize_name(self.name())

        code = f'''def {func_name}(state: AgentState) -> AgentState:
    """{self.get_description()}"""
    from airunner.components.llm.core.tool_registry import ToolRegistry
    
    tool_info = ToolRegistry.get("{tool_name}")
    if not tool_info:
        logger.error(f"Tool '{tool_name}' not found")
        state["error"] = f"Tool '{tool_name}' not found"
        return state
    
    tool_input = state.get("{input_key}")
    
    try:
        # Execute tool
        if isinstance(tool_input, dict):
            result = tool_info.func(**tool_input)
        elif isinstance(tool_input, (list, tuple)):
            result = tool_info.func(*tool_input)
        else:
            result = tool_info.func(tool_input)
        
        state["{output_key}"] = result
        logger.info(f"Tool '{tool_name}' executed successfully")
    
    except Exception as e:
        logger.error(f"Tool execution error: {{e}}")
        state["error"] = str(e)
    
    return state'''

        return code

    def get_input_state_keys(self) -> List[str]:
        """Get state keys this node reads from."""
        return [self.get_property("input_key")]

    def get_output_state_keys(self) -> List[str]:
        """Get state keys this node writes to."""
        return [self.get_property("output_key")]

    @staticmethod
    def _sanitize_name(name: str) -> str:
        """Sanitize node name to valid Python identifier."""
        sanitized = "".join(
            c if c.isalnum() or c == "_" else "_" for c in name
        )
        if sanitized and sanitized[0].isdigit():
            sanitized = f"node_{sanitized}"
        return sanitized or "tool_node"
