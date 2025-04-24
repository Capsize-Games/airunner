from airunner.gui.widgets.nodegraph.nodes.logic.base_logic_node import (
    BaseLogicNode,
)


class ForLoopNode(BaseLogicNode):
    """
    A node that iterates from a first index to a last index.

    Similar to Unreal Engine's ForLoop node, this node has:
    - An exec input to start the loop
    - A loop body exec output that triggers for each iteration
    - First index and last index inputs to control the range
    - Index output for the current iteration
    - A completed exec output triggered when the loop finishes
    """

    NODE_NAME = "For Loop"

    def __init__(self):
        super().__init__()

        # Add first index input port
        self.add_input("First Index", display_name=True)

        # Add last index input port
        self.add_input("Last Index", display_name=True)

        # Add current index output port
        self.add_output("Index", display_name=True)

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
        Executes the For loop from first_index to last_index.

        In a real implementation, this would need to handle execution flow differently
        to actually iterate through each index. This implementation simulates
        the concept but doesn't actually perform the iteration as that would
        require more changes to the execution engine.

        Returns:
            dict: Output data with current index
        """
        # Get the first and last indices
        first_index = self.get_input_data("First Index", input_data, 0)
        if not isinstance(first_index, (int, float)):
            try:
                first_index = int(first_index)
            except (TypeError, ValueError):
                first_index = 0

        last_index = self.get_input_data("Last Index", input_data, 0)
        if not isinstance(last_index, (int, float)):
            try:
                last_index = int(last_index)
            except (TypeError, ValueError):
                last_index = 0

        # Ensure we have integers
        first_index = int(first_index)
        last_index = int(last_index)

        if first_index <= last_index:
            # For demonstration, just use the first index value
            # In a real implementation, this would need to connect back to the execution
            # engine to process each index in sequence
            current_index = first_index

            print(
                f"{self.name()}: Processing index {current_index} (range: {first_index} to {last_index})"
            )

            # Return the current index
            return {
                "Index": current_index,
                # Trigger the loop body output for iteration
                "_exec_triggered": self.LOOP_BODY_PORT_NAME,
            }
        else:
            # If there's no valid range, trigger completed
            print(
                f"{self.name()}: No valid range ({first_index} to {last_index}), completing loop"
            )
            return {"_exec_triggered": self.COMPLETED_PORT_NAME}
