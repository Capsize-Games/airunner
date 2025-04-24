from airunner.gui.widgets.nodegraph.nodes.llm.base_llm_node import (
    BaseLLMNode,
)


class AgentActionNode(BaseLLMNode):
    NODE_NAME = "Agent Action"

    def __init__(self):
        super().__init__()
        # Default ports - can be customized via properties or methods
        self.add_input("in_message")
        self.add_output("out_message")
        # Add a text input widget to specify the action class/name
        self.add_text_input("action_name", "Action Name", tab="widgets")

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
