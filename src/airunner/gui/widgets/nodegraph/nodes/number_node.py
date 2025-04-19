from NodeGraphQt.constants import NodePropWidgetEnum
from airunner.gui.widgets.nodegraph.nodes.base_workflow_node import (
    BaseWorkflowNode,
)


class NumberNode(BaseWorkflowNode):
    """
    A node that outputs a numeric value.

    This node has a widget that allows the user to enter a number,
    which is then output as an integer.
    """

    NODE_NAME = "Number"
    has_exec_in_port = False
    has_exec_out_port = False

    def __init__(self):
        super().__init__()

        # Output port for the number
        self.out_port = self.add_output("value")

        self.add_text_input(
            name="number_value",
            label="Value",
            text="0",
            tooltip="Enter a number",
            tab="settings",
        )

    def execute(self, input_data):
        """
        Execute the node to output the numeric value.

        Returns:
            dict: A dictionary with the key 'value' containing the integer value.
        """
        try:
            # Get the number from the property and convert it to integer
            value = int(self.get_property("number_value"))
        except (ValueError, TypeError):
            # If conversion fails, default to 0
            value = 0
        return {"value": value}
