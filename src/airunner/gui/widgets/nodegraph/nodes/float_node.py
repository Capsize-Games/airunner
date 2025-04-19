from NodeGraphQt.constants import NodePropWidgetEnum
from airunner.gui.widgets.nodegraph.nodes.base_workflow_node import (
    BaseWorkflowNode,
)


class FloatNode(BaseWorkflowNode):
    """
    A node that outputs a floating point value.

    This node has a text input widget that allows the user to enter a number,
    which is then output as a float.
    """

    NODE_NAME = "Float"
    has_exec_in_port = False
    has_exec_out_port = False

    def __init__(self):
        super().__init__()

        # Output port for the float value
        self.add_output("value")

        # Add a proper float input using built-in NodeGraphQt widget type
        self.create_property(
            "float_value",
            0.0,
            widget_type=NodePropWidgetEnum.FLOAT.value,
            range=(0.0, 100.0),
            tab="settings",
        )

        # Add precision control using NodeGraphQt's built-in integer widget
        self.create_property(
            "precision",
            2,
            widget_type=NodePropWidgetEnum.INT.value,
            range=(0, 10),
            tab="settings",
        )

    def execute(self, input_data):
        """
        Execute the node to output the float value.

        Returns:
            dict: A dictionary with the key 'value' containing the float value.
        """
        try:
            # Get the float from the property
            float_value = float(self.get_property("float_value"))

            # Apply precision if specified
            precision = int(self.get_property("precision"))
            if precision >= 0:
                float_value = round(float_value, precision)

        except (ValueError, TypeError):
            # If conversion fails, default to 0.0
            float_value = 0.0

        return {"value": float_value}
