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
        self._pending_request = False
        super().__init__()
        self.image_request_port = self.add_input(
            "image_request", display_name=True
        )
        self.image_response_port = self.add_output(
            "image_response", display_name=True
        )

    def _generate_image(self, image_request: ImageRequest):
        # Store the current node ID with the request to identify this node
        image_request.node_id = self.id

        # Emit signal to generate the image
        self.emit_signal(
            SignalCode.DO_GENERATE_SIGNAL,
            {
                "image_request": image_request,
            },
        )

    def _on_image_generated(self, data: Dict):
        image_response = data.get("message", None)
        if image_response is None:
            # Send completion signal with empty output data
            self.emit_signal(
                SignalCode.NODE_EXECUTION_COMPLETED_SIGNAL,
                {
                    "node_id": self.id,
                    "result": self.EXEC_OUT_PORT_NAME,
                    "output_data": {"image_response": None, "image": None},
                },
            )
            self._pending_request = False
            return

        # Verify this response belongs to this node
        if image_response.node_id is None or image_response.node_id != self.id:
            return

        # Mark that request is no longer pending
        self._pending_request = False

        # Prepare output data that will be passed to connected nodes
        output_data = {
            "image_response": image_response,
            "image_response": (
                image_response.images[0] if image_response.images else None
            ),
        }

        # Emit signal that execution is complete with the result and output data
        # This continues the workflow execution at this node
        self.emit_signal(
            SignalCode.NODE_EXECUTION_COMPLETED_SIGNAL,
            {
                "node_id": self.id,
                "result": self.EXEC_OUT_PORT_NAME,
                "output_data": output_data,  # Include the output data in the signal
            },
        )
        self.emit_signal(SignalCode.SD_UNLOAD_SIGNAL)

    def execute(self, input_data: Dict):
        """
        Execute the node to generate an image.

        If this is the first execution, start image generation and return None
        to indicate pending execution.
        """
        # Check if we're already waiting for generation
        if self._pending_request:
            self.logger.warning(
                f"Node {self.id} is already waiting for image generation"
            )
            return None

        # Get image request from input
        image_request = input_data.get("image_request", None)
        if image_request is None:
            self.logger.error("No image request provided to GenerateImageNode")
            return {"image_response": None, "image": None}

        # Mark as pending and initiate image generation
        self.logger.info(f"Starting image generation for node {self.id}")
        image_request.node_id = self.id
        self._generate_image(image_request)
        self._pending_request = True

        # Return None to indicate the node execution is pending
        # The NodeGraphWorker will pause execution until NODE_EXECUTION_COMPLETED_SIGNAL
        return None
