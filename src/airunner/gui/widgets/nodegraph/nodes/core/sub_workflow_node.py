from NodeGraphQt.constants import NodePropWidgetEnum

from airunner.gui.widgets.nodegraph.nodes.core.base_core_node import (
    BaseCoreNode,
)
from airunner.data.models.workflow import Workflow


class SubWorkflowNode(BaseCoreNode):
    """
    A node that represents a saved workflow that can be used within other workflows.

    This allows for creating reusable, nested workflows and building complex
    workflow hierarchies.
    """

    NODE_NAME = "Workflow"

    def __init__(self):
        super().__init__()

        # Reference to the actual workflow this node represents
        self._workflow_id = None
        self._workflow_name = "None"

        # Create properties for workflow selection
        self.create_property(
            "workflow_id",
            None,
            widget_type=NodePropWidgetEnum.QCOMBO_BOX.value,
            items=self._get_workflow_names(),
            tab="settings",
        )

        # Create property for workflow description
        self.create_property(
            "workflow_description",
            "Select a workflow",
            widget_type=NodePropWidgetEnum.QLABEL.value,
            tab="settings",
        )

    def _get_workflow_names(self):
        """Get names of available workflows for combo box"""
        # Note: This should ideally be using a dependency-injected session
        # This is a placeholder that should be replaced with your actual DB session
        try:
            from airunner.data.session import Session

            with Session() as session:
                workflows = session.query(Workflow).all()
                return [
                    {"workflow.name": w.name, "workflow.id": w.id}
                    for w in workflows
                ]
        except Exception as e:
            print(f"Error loading workflows: {e}")
            return []

    def set_workflow(self, workflow_id):
        """Set the workflow this node represents"""
        self._workflow_id = workflow_id

        # Load the workflow details
        try:
            from airunner.data.session import Session

            with Session() as session:
                workflow = (
                    session.query(Workflow).filter_by(id=workflow_id).first()
                )
                if workflow:
                    self._workflow_name = workflow.name
                    self.set_property(
                        "workflow_description",
                        f"Description: {workflow.description}",
                    )

                    # Update node name to reflect the workflow
                    self.set_name(f"Workflow: {workflow.name}")

                    # Configure ports based on the workflow's inputs and outputs
                    self._configure_ports_from_workflow(workflow)
        except Exception as e:
            print(f"Error setting workflow: {e}")

    def _configure_ports_from_workflow(self, workflow):
        """Configure the node's ports based on the referenced workflow"""
        # This is a simplified version - in a real implementation, you would:
        # 1. Analyze the workflow to find "start" nodes (input points)
        # 2. Analyze the workflow to find terminal nodes (output points)
        # 3. Create corresponding ports on this node

        # For now, we just have the standard exec in/out ports
        # Additional data ports could be derived from analyzing the workflow
        pass

    def execute(self, input_data):
        """
        Execute the sub-workflow.

        In a full implementation, this would:
        1. Load the referenced workflow
        2. Execute it with the provided inputs
        3. Return its outputs
        """
        if not self._workflow_id:
            print(f"No workflow selected for node {self.name()}")
            return {}

        print(
            f"Executing sub-workflow: {self._workflow_name} (ID: {self._workflow_id})"
        )

        # This is a placeholder. In a real implementation, you would:
        # 1. Load the workflow's nodes and connections
        # 2. Execute the workflow in its own context
        # 3. Return the results

        # For now, just pass through
        return {"_exec_triggered": self.EXEC_OUT_PORT_NAME}
