from airunner.gui.widgets.nodegraph.nodes.core.base_core_node import (
    BaseCoreNode,
)


class StartNode(BaseCoreNode):
    NODE_NAME = "Start Workflow"
    has_exec_in_port: bool = False

    def __init__(self):
        super().__init__()

        # Set a distinctive color to make the StartNode easily recognizable
        self.set_color(50, 150, 250)  # Light blue color

        # Remove the input exec port as this is the first node in the workflow
        if self.EXEC_IN_PORT_NAME in self.inputs():
            self.delete_input(self.EXEC_IN_PORT_NAME)

    # No specific execution logic needed here, it just starts the flow
    def execute(self, input_data):
        # Simply forward the execution flow to the next nodes
        return {"_exec_triggered": self.EXEC_OUT_PORT_NAME}
