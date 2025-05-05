from typing import Dict

from airunner.gui.widgets.nodegraph.nodes.art.base_art_node import (
    BaseArtNode,
)
from airunner.handlers.stablediffusion.image_request import ImageRequest
from airunner.enums import SignalCode
from airunner.handlers.stablediffusion.image_response import ImageResponse
from NodeGraphQt.constants import NodePropWidgetEnum


class GenerateImageNode(BaseArtNode):
    """
    Node for generating images using a specified Stable Diffusion model
    """

    NODE_NAME = "Generate Image"
    _input_ports = [
        {"name": "controlnet", "display_name": True},
        {"name": "image_to_image", "display_name": True},
        {"name": "image_request", "display_name": True},
    ]
    _output_ports = [
        {"name": "image_response", "display_name": True},
        {"name": "image", "display_name": True},
    ]
    _propertes = [
        {
            "name": "unload_after_generation",
            "value": True,
            "widget_type": NodePropWidgetEnum.QCHECK_BOX.value,
            "tab": "basic",
        }
    ]

    def __init__(self):
        self.signal_handlers = {
            SignalCode.ENGINE_RESPONSE_WORKER_RESPONSE_SIGNAL: self._on_image_generated
        }
        self._pending_request = False
        super().__init__()

    def _generate_image(self, image_request: ImageRequest):
        # Store the current node ID with the request to identify this node
        image_request.node_id = self.id
        self.api.art.send_request(image_request)

    def _on_image_generated(self, data: Dict):
        image_response = data.get("message", None)
        if image_response is None:
            # Send completion signal with empty output data
            self.api.nodegraph.node_executed(
                node_id=self.id,
                result=self.EXEC_OUT_PORT_NAME,
                data={"image_response": None, "image": None},
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
        }

        # Emit signal that execution is complete with the result and output data
        # This continues the workflow execution at this node
        self.api.nodegraph.node_executed(
            node_id=self.id,
            result=self.EXEC_OUT_PORT_NAME,
            data=output_data,  # Include the output data in the node execution
        )

        if self.get_property("unload_after_generation"):
            self.api.art.unload()

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

    def on_stop(self):
        super().on_stop()
        self.api.art.interrupt_generate()
