from airunner.gui.widgets.nodegraph.nodes.logic.base_logic_node import (
    BaseLogicNode,
)


class WhileLoopNode(BaseLogicNode):
    """
    A node that continues to loop while a condition is true.

    Similar to Unreal Engine's WhileLoop node, this node has:
    - An exec input to start the loop
    - A loop body exec output that triggers for each iteration
    - A condition input to control loop continuation
    - A completed exec output triggered when the loop finishes (condition is false)
    """

    NODE_NAME = "While Loop"

    def __init__(self):
        super().__init__()

        # Add condition input port
        self.add_input("Condition", display_name=True)

        # Add loop body execution output port (triggers for each iteration)
        self.add_output(
            self.LOOP_BODY_PORT_NAME,
            display_name=True,
            painter_func=self._draw_exec_port,
        )

        # Add completed execution output port (triggers when loop finishes)
        self.add_output(
            self.COMPLETED_PORT_NAME,
            display_name=True,
            painter_func=self._draw_exec_port,
        )

    def execute(self, input_data):
        """
        Executes the While loop based on the input condition.

        In a real implementation, this would need to handle execution flow differently
        to actually iterate based on condition. This implementation simulates
        the concept but doesn't actually perform the iteration as that would
        require more changes to the execution engine.

        Returns:
            dict: Output data with triggered execution port
        """
        # Get the condition value
        condition = self.get_input_data("Condition", input_data, False)

        # Convert to boolean if needed
        if not isinstance(condition, bool):
            if isinstance(condition, (int, float)):
                condition = bool(condition)
            elif isinstance(condition, str):
                condition = condition.lower() in ("true", "yes", "1", "t", "y")
            else:
                condition = False

        if condition:
            print(f"{self.name()}: Condition is True, continuing loop")

            # Trigger the loop body output
            return {"_exec_triggered": self.LOOP_BODY_PORT_NAME}
        else:
            # If condition is false, trigger completed
            print(f"{self.name()}: Condition is False, completing loop")
            return {"_exec_triggered": self.COMPLETED_PORT_NAME}
