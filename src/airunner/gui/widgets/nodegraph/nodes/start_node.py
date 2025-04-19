from airunner.gui.widgets.nodegraph.nodes.base_workflow_node import (
    BaseWorkflowNode,
)


class StartNode(BaseWorkflowNode):
    NODE_NAME = "Start Workflow"
    __identifier__ = "airunner.workflow.nodes.control"  # Specific identifier for control flow
    # NODE_PORTS_REMOVABLE = True # Class attribute might not be working reliably
    has_exec_in_port: bool = False

    def __init__(self):
        super().__init__()
        # self._ports_removable = True  # Set instance variable to allow port deletion permanently for this node type
        # Start node only has an execution output, remove the input exec port
        # self.delete_input(self.EXEC_IN_PORT_NAME)
        # No need to set it back to False

        # Optionally, remove all data inputs/outputs if it purely signals start
        # for name in list(self.inputs().keys()):
        #     if name != self.EXEC_IN_PORT_NAME: self.delete_input(name)
        # for name in list(self.outputs().keys()):
        #      if name != self.EXEC_OUT_PORT_NAME: self.delete_output(name)

    # No specific execution logic needed here, it just starts the flow
    def execute(self, input_data):
        print(f"Executing {self.NODE_NAME}")
        # Base execute handles passing execution signal, return empty data dict
        return {}
