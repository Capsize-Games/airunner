from typing import Dict

from airunner.gui.widgets.nodegraph.nodes.art.base_art_node import (
    BaseArtNode,
)
from airunner.handlers.stablediffusion.image_request import ImageRequest
from airunner.enums import SignalCode


class GenerateImageNode(BaseArtNode):
    """
    Node for generating images using a specified Stable Diffusion model
    """

    NODE_NAME = "Generate Image"

    def __init__(self):
        self.signal_handlers = {}
        super().__init__()
        self.image_request_port = self.add_input(
            "image_request", display_name=True
        )
        self.image_response_port = self.add_output(
            "image_response", display_name=True
        )

    def _generate_image(self, image_request: ImageRequest):
        self.emit_signal(
            SignalCode.DO_GENERATE_SIGNAL,
            {
                "image_request": image_request,
            },
        )

    def _on_image_generated(self, data: Dict):
        print("ON IMAGE GENERATED CALLBACK HERE", data)

    def execute(self, input_data: Dict):
        image_request = input_data.get("image_request", None)
        print("*" * 100)
        print("image_request", image_request)
        if image_request is not None:
            image_request.callback = self._on_image_generated
            self._generate_image(image_request)
        return {}
