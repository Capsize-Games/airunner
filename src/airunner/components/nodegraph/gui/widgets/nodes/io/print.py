from typing import Any, Dict
from airunner.components.nodegraph.gui.widgets.nodes.core.base_workflow_node import (
    BaseWorkflowNode,
)
from airunner.vendor.nodegraphqt.constants import NodePropWidgetEnum


class PrintNode(BaseWorkflowNode):
    NODE_NAME = "Print"
    __identifier__ = "IO.PrintNode"
    has_exec_in_port = True
    has_exec_out_port = False
    _input_ports = [
        dict(name="print_statement", display_name="Print Statement"),
    ]
    _properties = [
        dict(
            name="print_statement",
            value="",
            widget_type=NodePropWidgetEnum.QLINE_EDIT,
            tab="settings",
        ),
    ]

    def execute(self, input_data: Dict[str, Any]):
        """
        Execute the print node by printing the input data to the console.
        """
        print_statement = input_data.get("print_statement", "")
        print(print_statement)

        # No output ports to handle
        return {}
