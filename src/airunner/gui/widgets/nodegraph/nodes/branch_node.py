from airunner.gui.widgets.nodegraph.nodes.base_workflow_node import (
    BaseWorkflowNode,
)


class BranchNode(BaseWorkflowNode):
    NODE_NAME = "Branch"
    __identifier__ = "airunner.workflow.nodes.control"  # Specific identifier for control flow
    has_exec_out_port: bool = False

    # Define constants for the execution output ports
    EXEC_OUT_TRUE = "exec_out_true"
    EXEC_OUT_FALSE = "exec_out_false"

    def __init__(self):
        super().__init__()

        # Add the condition input port (remove data_type argument)
        self.add_input("condition")

        # Add specific execution outputs for True and False branches
        # Use the same painter function as the base exec ports
        self.add_output(
            self.EXEC_OUT_TRUE,
            display_name=True,
            painter_func=self._draw_exec_port,
        )
        self.add_output(
            self.EXEC_OUT_FALSE,
            display_name=True,
            painter_func=self._draw_exec_port,
        )

        # Optionally remove data outputs if this node only directs flow
        # for name in list(self.outputs().keys()):
        #     if name not in [self.EXEC_OUT_TRUE, self.EXEC_OUT_FALSE]:
        #         self.delete_output(name)

    def execute(self, input_data):
        condition = self.get_input_data("condition", input_data, default=False)
        print(f"Executing {self.NODE_NAME} with condition: {condition}")

        # Determine which execution path to trigger based on the condition
        if condition:
            # Indicate that the 'True' execution path should be followed
            return {"_exec_triggered": self.EXEC_OUT_TRUE}
        else:
            # Indicate that the 'False' execution path should be followed
            return {"_exec_triggered": self.EXEC_OUT_FALSE}
