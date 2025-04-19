from airunner.gui.widgets.nodegraph.nodes.base_workflow_node import (
    BaseWorkflowNode,
)


class BooleanNode(BaseWorkflowNode):
    """
    A node that outputs a boolean value.

    This node has a checkbox widget that allows the user to set a boolean value,
    which is then output as a boolean.
    """

    NODE_NAME = "Boolean"
    has_exec_in_port: bool = False
    has_exec_out_port: bool = False

    def __init__(self):
        super().__init__()

        # Output port for the boolean value
        self.add_output("value")

        # Add a checkbox for the boolean value
        self.add_checkbox(
            name="boolean_value",
            label="Value",
            text="Enabled",
            state=False,
            tooltip="Toggle to switch between True and False",
            tab="settings",
        )

    def execute(self, input_data):
        """
        Execute the node to output the boolean value.

        Returns:
            dict: A dictionary with the key 'value' containing the boolean value.
        """
        # Get the boolean from the checkbox
        value = bool(self.get_property("boolean_value"))

        return {"value": value}
