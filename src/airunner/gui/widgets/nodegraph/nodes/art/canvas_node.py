from airunner.gui.widgets.nodegraph.nodes.art.base_art_node import (
    BaseArtNode,
)
from airunner.enums import SignalCode

class CanvasNode(BaseArtNode):
    NODE_NAME = "Canvas Node"

    def __init__(self):
        super().__init__()

        # Input port for ImageResponse object
        self.add_input("image_response_in")
        self.add_output("image_response_out")

    def execute(self, input_data):
        image_response = self.get_input_data("image_response", input_data)
        # # Return empty dict as this node primarily displays data
        # # Execution flow is handled by the graph executor via exec ports
        self.emit_signal(
            SignalCode.SEND_IMAGE_TO_CANVAS_SIGNAL,
            {"image_response": image_response},
        )
        return {}
