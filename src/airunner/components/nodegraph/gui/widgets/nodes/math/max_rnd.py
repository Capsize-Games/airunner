from airunner.components.nodegraph.gui.widgets.nodes.math.base_math_node import (
    BaseMathNode,
)
from airunner.settings import AIRUNNER_MAX_SEED


class MaxRND(BaseMathNode):
    NODE_NAME = "Max RND Number"
    has_exec_in_port = False
    has_exec_out_port = False
    _input_ports = []
    _output_ports = [
        dict(name="max_seed", display_name="Max Seed"),
    ]
    _properties = []

    def execute(self, input_data):
        return {"max_seed": AIRUNNER_MAX_SEED}
