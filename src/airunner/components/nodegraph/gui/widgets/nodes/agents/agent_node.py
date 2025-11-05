"""Agent Node for executing saved LangGraph workflows.

This node represents a saved LangGraph workflow that can be executed
as a reusable agent within AI Runner workflows.
"""

from typing import Dict, Any, Optional
from airunner.components.nodegraph.gui.widgets.nodes.core.base_workflow_node import (
    BaseWorkflowNode,
)
from airunner.vendor.nodegraphqt.constants import NodePropWidgetEnum


class AgentNode(BaseWorkflowNode):
    """Node representing a saved LangGraph workflow as an executable agent.

    This node is dynamically created when a LangGraph workflow is saved.
    It contains the inputs and outputs defined in the LangGraph workflow
    and executes the workflow when triggered.

    Attributes:
        __identifier__: Namespace for agent nodes
        NODE_NAME: Display name of the node
        langgraph_workflow_id: ID of the source LangGraph workflow
        node_color: Visual color (green for agents)
    """

    __identifier__ = "airunner.agents"
    NODE_NAME = "Agent"

    # Visual styling
    node_color = (100, 200, 100)  # Green color for agents

    def __init__(self):
        """Initialize Agent node."""
        super().__init__()
        self.langgraph_workflow_id: Optional[int] = None

    def add_custom_property(
        self, name: str, value: Any, widget_type: NodePropWidgetEnum, **kwargs
    ):
        """Add a custom property to the node.

        Args:
            name: Property name
            value: Default value
            widget_type: Widget type for editing
            **kwargs: Additional property kwargs (tab, range, etc.)
        """
        self.add_property(
            name,
            value,
            widget_type=widget_type,
            tab="properties",
            **kwargs,
        )

    def set_workflow_metadata(
        self, workflow_id: int, workflow_name: str, description: str = ""
    ):
        """Set metadata from the source LangGraph workflow.

        Args:
            workflow_id: ID of the LangGraph workflow
            workflow_name: Name of the workflow
            description: Description of the workflow
        """
        self.langgraph_workflow_id = workflow_id
        self.set_name(workflow_name)

        # Add workflow info as a read-only property
        self.add_property(
            "workflow_id",
            workflow_id,
            widget_type=NodePropWidgetEnum.QLABEL,
            tab="info",
        )
        if description:
            self.add_property(
                "description",
                description,
                widget_type=NodePropWidgetEnum.QTEXT_EDIT,
                tab="info",
            )

    def execute(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the agent by running its LangGraph workflow.

        Args:
            data: Input data for the workflow

        Returns:
            Output data from the workflow
        """
        if not self.langgraph_workflow_id:
            self.logger.error(
                "Agent node has no associated LangGraph workflow"
            )
            return {}

        # TODO: Implement LangGraph workflow execution
        # This will need to:
        # 1. Load the LangGraph workflow from database
        # 2. Convert it to executable LangGraph code
        # 3. Run the workflow with input data
        # 4. Return the output

        self.logger.info(
            f"Executing agent node '{self.name()}' "
            f"(workflow ID: {self.langgraph_workflow_id})"
        )

        # For now, pass through the data
        return data

    @classmethod
    def create_from_langgraph_workflow(
        cls,
        workflow_id: int,
        workflow_name: str,
        description: str,
        inputs: Dict[str, str],
        outputs: Dict[str, str],
    ) -> "AgentNode":
        """Create an Agent node from a LangGraph workflow definition.

        Args:
            workflow_id: ID of the LangGraph workflow
            workflow_name: Name of the workflow
            description: Description
            inputs: Dict of input port names to types
            outputs: Dict of output port names to types

        Returns:
            Configured AgentNode instance
        """
        node = cls()
        node.set_workflow_metadata(workflow_id, workflow_name, description)

        # Add input ports dynamically
        for port_name, port_type in inputs.items():
            node.add_input(port_name, color=(200, 200, 100))

        # Add output ports dynamically
        for port_name, port_type in outputs.items():
            node.add_output(port_name, color=(100, 200, 200))

        return node
