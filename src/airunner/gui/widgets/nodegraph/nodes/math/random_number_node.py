# Random Number Generator Node
import random
from NodeGraphQt.constants import NodePropWidgetEnum
from airunner.gui.widgets.nodegraph.nodes.math.base_math_node import (
    BaseMathNode,
)


class RandomNumberNode(BaseMathNode):
    NODE_NAME = "Random Number Generator"
    has_exec_in_port = False
    has_exec_out_port = False

    def __init__(self):
        super().__init__()

        # Inputs for min and max values
        self.add_input("min")
        self.add_input("max")

        # Output for the random number
        self.add_output("random_value")

        # Add default min value using NodeGraphQt's built-in integer widget
        self.create_property(
            "default_min",
            0,
            widget_type=NodePropWidgetEnum.INT.value,
            range=(-1000, 1000),
            tab="settings",
        )

        # Add default max value using NodeGraphQt's built-in integer widget
        self.create_property(
            "default_max",
            100,
            widget_type=NodePropWidgetEnum.INT.value,
            range=(-1000, 1000),
            tab="settings",
        )

    def execute(self, input_data):
        # Get input values or use defaults from property widgets
        try:
            min_val = input_data.get("min")
            if min_val is None:
                min_val = int(self.get_property("default_min"))
            else:
                min_val = int(min_val)

            max_val = input_data.get("max")
            if max_val is None:
                max_val = int(self.get_property("default_max"))
            else:
                max_val = int(max_val)

            # Ensure min is less than max
            if min_val > max_val:
                min_val, max_val = max_val, min_val

            # Generate random number
            random_value = random.randint(min_val, max_val)

            return {"random_value": random_value}
        except (ValueError, TypeError) as e:
            print(f"Error in RandomNumberNode: {e}")
            # Return a default value if there's an error
            return {"random_value": 0}
