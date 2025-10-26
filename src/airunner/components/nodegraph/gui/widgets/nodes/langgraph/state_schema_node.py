"""State Schema Node for defining workflow state.

This node allows users to define the state structure for their
LangGraph workflow visually.
"""

from typing import Dict
from airunner.vendor.nodegraphqt.constants import NodePropWidgetEnum
from airunner.components.nodegraph.gui.widgets.nodes.langgraph.base_langgraph_node import (
    BaseLangGraphNode,
)


class StateSchemaNode(BaseLangGraphNode):
    """Define the state schema for a LangGraph workflow.

    This node outputs a state schema that other nodes can use.
    It's typically placed at the beginning of the workflow.
    """

    NODE_NAME = "State Schema"

    # This node has no execution ports - it's just for definition
    has_exec_in_port = False
    has_exec_out_port = False

    _output_ports = [
        dict(name="state_schema", display_name="State Schema"),
    ]

    _properties = [
        dict(
            name="state_name",
            value="AgentState",
            widget_type=NodePropWidgetEnum.QLINE_EDIT,
            tab="basic",
        ),
        dict(
            name="state_type",
            value="base",
            widget_type=NodePropWidgetEnum.QCOMBO_BOX,
            items=["base", "rag", "tool", "custom"],
            tab="basic",
        ),
        dict(
            name="custom_fields",
            value="{}",
            widget_type=NodePropWidgetEnum.QTEXT_EDIT,
            tab="custom",
        ),
    ]

    def get_node_type(self) -> str:
        """Get node type identifier."""
        return "state_schema"

    def get_description(self) -> str:
        """Get node description."""
        return "Define workflow state schema"

    def to_langgraph_code(self) -> str:
        """Generate Python code for state definition.

        Returns:
            Python code string
        """
        state_name = self.get_property("state_name")
        state_type = self.get_property("state_type")
        custom_fields = self.get_property("custom_fields")

        # Base imports and class definition
        code_lines = [
            "from typing import TypedDict, List, Dict, Any, Optional",
            "",
            f"class {state_name}(TypedDict):",
            f'    """{self.get_description()}"""',
        ]

        # Add fields based on type
        if state_type == "base":
            code_lines.extend(
                [
                    "    messages: List[str]",
                    "    next_action: str",
                    "    error: Optional[str]",
                    "    metadata: Dict[str, Any]",
                ]
            )
        elif state_type == "rag":
            code_lines.extend(
                [
                    "    messages: List[str]",
                    "    next_action: str",
                    "    error: Optional[str]",
                    "    metadata: Dict[str, Any]",
                    "    rag_context: str",
                    "    retrieved_docs: List[Dict[str, Any]]",
                    "    query: str",
                ]
            )
        elif state_type == "tool":
            code_lines.extend(
                [
                    "    messages: List[str]",
                    "    next_action: str",
                    "    error: Optional[str]",
                    "    metadata: Dict[str, Any]",
                    "    tool_calls: List[Dict[str, Any]]",
                    "    tool_results: List[Any]",
                    "    current_tool: Optional[str]",
                ]
            )
        elif state_type == "custom":
            # Parse custom fields
            try:
                import json

                fields = json.loads(custom_fields)
                for field_name, field_type in fields.items():
                    code_lines.append(f"    {field_name}: {field_type}")
            except Exception:
                code_lines.append("    # Error parsing custom fields")
                code_lines.append("    messages: List[str]")

        return "\n".join(code_lines)

    def get_state_class_name(self) -> str:
        """Get the name of the state class.

        Returns:
            State class name
        """
        return self.get_property("state_name")

    def get_state_fields(self) -> Dict[str, str]:
        """Get the state fields as a dictionary.

        Returns:
            Dict of field_name: type_string
        """
        state_type = self.get_property("state_type")
        custom_fields = self.get_property("custom_fields")

        if state_type == "base":
            return {
                "messages": "List[str]",
                "next_action": "str",
                "error": "Optional[str]",
                "metadata": "Dict[str, Any]",
            }
        elif state_type == "rag":
            return {
                "messages": "List[str]",
                "next_action": "str",
                "error": "Optional[str]",
                "metadata": "Dict[str, Any]",
                "rag_context": "str",
                "retrieved_docs": "List[Dict[str, Any]]",
                "query": "str",
            }
        elif state_type == "tool":
            return {
                "messages": "List[str]",
                "next_action": "str",
                "error": "Optional[str]",
                "metadata": "Dict[str, Any]",
                "tool_calls": "List[Dict[str, Any]]",
                "tool_results": "List[Any]",
                "current_tool": "Optional[str]",
            }
        elif state_type == "custom":
            try:
                import json

                return json.loads(custom_fields)
            except Exception:
                return {"messages": "List[str]"}

        return {}
