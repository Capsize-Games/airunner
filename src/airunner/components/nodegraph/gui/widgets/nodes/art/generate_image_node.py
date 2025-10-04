from typing import Dict

from airunner.components.nodegraph.gui.widgets.nodes.art.base_art_node import (
    BaseArtNode,
)
from airunner.components.art.managers.stablediffusion.image_request import (
    ImageRequest,
)
from airunner.components.art.managers.stablediffusion.image_response import (
    ImageResponse,
)
from airunner.enums import SignalCode
from airunner.vendor.nodegraphqt.constants import NodePropWidgetEnum


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
        code = data.get("code", None)
        msg = data.get("message", None)

        # If the worker returned an ImageResponse, handle normally.
        if isinstance(msg, ImageResponse):
            image_response = msg
        else:
            # Non-image responses (error strings, interrupted notifications)
            # should be treated as a failed/aborted generation for this node.
            try:
                self.api.nodegraph.node_executed(
                    node_id=data.get("node_id", self.id),
                    result=self.EXEC_OUT_PORT_NAME,
                    data={"image_response": None, "image": None},
                )
            except Exception:
                pass
            self._pending_request = False
            return

        if image_response.node_id is None or image_response.node_id != self.id:
            return

        self._pending_request = False

        output_data = {
            "image_response": image_response,
            "image": (
                image_response.images[0]
                if image_response and image_response.images
                else None
            ),
        }

        self.api.nodegraph.node_executed(
            node_id=self.id,
            result=self.EXEC_OUT_PORT_NAME,
            data=output_data,
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
