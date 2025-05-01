from NodeGraphQt.constants import NodePropWidgetEnum

from airunner.gui.widgets.nodegraph.nodes.llm.base_llm_node import (
    BaseLLMNode,
)


class AgentActionNode(BaseLLMNode):
    NODE_NAME = "Agent Action"
    _input_ports = [
        dict(name="in_message", display_name="Input Message"),
    ]
    _output_ports = [
        dict(name="out_message", display_name="Output Message"),
    ]
    _properties = [
        dict(
            name="action_name",
            value="",
            widget_type=NodePropWidgetEnum.QLINE_EDIT,
            tab="action",
        ),
    ]

    # Override execute for AgentAction specific logic (placeholder)
    def execute(self, input_data):
        action_name = self.get_property("action_name")
        in_message = input_data.get(
            "in_message", None
        )  # Get data from the connected input port
        print(
            f"Executing Agent Action: {action_name} with input: {in_message}"
        )
        # Dummy logic: Find the corresponding AgentAction class based on action_name
        # and call its run method. For now, just pass data through.
        output_data = f"Action '{action_name}' processed: {in_message}"
        return {
            "out_message": output_data
        }  # Return data for the 'out_message' port
