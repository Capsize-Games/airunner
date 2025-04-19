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

    def __init__(self):
        super().__init__()

        # Output port for the number
        self.add_output("value")

        # Add an integer input using NodeGraphQt's built-in widget type
        self.create_property(
            "number_value",
            0,
            widget_type=NodePropWidgetEnum.INT.value,
            range=(-1000, 1000),
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
