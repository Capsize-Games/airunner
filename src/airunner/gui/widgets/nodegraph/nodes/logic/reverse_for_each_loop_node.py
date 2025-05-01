from airunner.gui.widgets.nodegraph.nodes.logic.base_logic_node import (
    BaseLogicNode,
)


class ReverseForEachLoopNode(BaseLogicNode):
    """
    A node that iterates over elements in an array/collection in reverse order.

    Similar to Unreal Engine's ReverseForEachLoop node, this node has:
    - An exec input to start the loop
    - A loop body exec output that triggers for each iteration
    - An array input for the collection to iterate through
    - Array element and array index outputs for the current iteration
    - A completed exec output triggered when the loop finishes
    """

    NODE_NAME = "Reverse For Each Loop"
    _input_ports = [
        dict(name="Array", display_name="Array"),
    ]
    _output_ports = [
        dict(name="Array Element", display_name="Array Element"),
        dict(name="Array Index", display_name="Array Index"),
        dict(name="Loop Body", display_name="Loop Body"),
        dict(name="Completed", display_name="Completed"),
    ]

    def execute(self, input_data):
        """
        Executes the Reverse ForEach loop over the input array in reverse order.

        In a real implementation, this would need to handle execution flow differently
        to actually iterate through each element of the array in reverse. This implementation
        simulates the concept but doesn't actually perform the iteration as that
        would require more changes to the execution engine.

        Returns:
            dict: Output data with array element and index
        """
        # Get the array from input data
        array = self.get_input_data("Array", input_data, [])

        # Validate array
        if not isinstance(array, (list, tuple)):
            print(
                f"Warning: 'Array' input to {self.name()} is not iterable. Using empty list."
            )
            array = []

        if array:
            # For demonstration, just use the last element
            # In a real implementation, this would need to connect back to the execution
            # engine to process each element in reverse sequence
            index = len(array) - 1
            element = array[index]

            print(
                f"{self.name()}: Processing element {element} at index {index} (in reverse)"
            )

            # Return the current element and index
            return {
                "Array Element": element,
                "Array Index": index,
                # Trigger the loop body output for iteration
                "_exec_triggered": self.LOOP_BODY_PORT_NAME,
            }
        else:
            # If array is empty, trigger completed
            print(f"{self.name()}: Array is empty, completing loop")
            return {"_exec_triggered": self.COMPLETED_PORT_NAME}
