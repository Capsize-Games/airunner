# Node representing a nested Workflow
from airunner.gui.widgets.nodegraph.nodes.core.base_core_node import (
    BaseCoreNode,
)


class WorkflowNode(BaseCoreNode):
    NODE_NAME = "Workflow"  # Default name

    _input_ports = [
        {"name": "start_flow", "display_name": True},
    ]
    _output_ports = [
        {"name": "flow_complete", "display_name": True},
    ]

    def __init__(self):
        super().__init__()
        self.add_text_input(
            "nested_workflow_id", "Workflow ID/Name", tab="widgets"
        )

    def execute(self, input_data):
        nested_workflow_id = self.get_property("nested_workflow_id")
        start_data = input_data.get("start_flow", None)
        self.logger.info(
            f"Executing nested Workflow: {nested_workflow_id} with start data: {start_data}"
        )
        output_data = f"Workflow '{nested_workflow_id}' completed, result from: {start_data}"
        return {"flow_complete": output_data}
