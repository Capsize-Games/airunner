# Node representing a nested Workflow
from airunner.gui.widgets.nodegraph.nodes.core.base_core_node import (
    BaseCoreNode,
)


class WorkflowNode(BaseCoreNode):
    NODE_NAME = "Workflow"  # Default name

    def __init__(self):
        super().__init__()
        # Ports for triggering and receiving results from the nested workflow
        self.add_input("start_flow")
        self.add_output("flow_complete")
        # Add a property to store the ID or name of the nested workflow
        self.add_text_input(
            "nested_workflow_id", "Workflow ID/Name", tab="widgets"
        )

    # Override execute for Workflow specific logic (placeholder)
    def execute(self, input_data):
        nested_workflow_id = self.get_property("nested_workflow_id")
        start_data = input_data.get("start_flow", None)
        print(
            f"Executing nested Workflow: {nested_workflow_id} with start data: {start_data}"
        )
        # Dummy logic: Load and execute the nested workflow based on nested_workflow_id.
        # For now, just pass data through.
        output_data = f"Workflow '{nested_workflow_id}' completed, result from: {start_data}"
        return {
            "flow_complete": output_data
        }  # Return data for the 'flow_complete' port
