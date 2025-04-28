import time
from typing import Dict

from airunner.gui.widgets.nodegraph.nodes.art.base_art_node import (
    BaseArtNode,
)
from airunner.handlers.stablediffusion.image_request import ImageRequest
from airunner.enums import SignalCode
from airunner.handlers.stablediffusion.image_response import ImageResponse


class GenerateImageNode(BaseArtNode):
    """
    Node for generating images using a specified Stable Diffusion model
    """

    NODE_NAME = "Generate Image"

    def __init__(self):
        self.signal_handlers = {
            SignalCode.ENGINE_RESPONSE_WORKER_RESPONSE_SIGNAL: self._on_image_generated
        }
        self.wait = False
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
        image_response = data.get("image_response", None)
        if image_response is not None:
            self.emit_signal(
                SignalCode.NODE_EXECUTION_COMPLETED_SIGNAL,
                {
                    "image": image_response.images[0],
                },
            )

    def execute(self, input_data: Dict):
        if not self.wait:
            self.wait = True
            image_request = input_data.get("image_request", None)
            if image_request is not None:
                self._generate_image(image_request)
        else:
            self.wait = False
            return {"image": input_data.get("image", None)}
