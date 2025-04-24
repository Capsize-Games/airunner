from airunner.gui.widgets.nodegraph.nodes.core.base_workflow_node import (
    BaseWorkflowNode,
)


class BaseLogicNode(BaseWorkflowNode):
    __identifier__ = "Logic"
    has_exec_out_port: bool = False
    LOOP_BODY_PORT_NAME = "Loop Body"
    COMPLETED_PORT_NAME = "Completed"
