from airunner.gui.widgets.nodegraph.nodes.base_workflow_node import (
    BaseWorkflowNode,
)
from airunner.handlers.stablediffusion.image_request import ImageRequest
from airunner.handlers.stablediffusion.image_response import ImageResponse
from airunner.handlers.stablediffusion.rect import Rect
from airunner.enums import ImagePreset
from airunner.settings import AIRUNNER_DEFAULT_SCHEDULER
import PIL.Image
import numpy as np
import random


class ImageGenerationNode(BaseWorkflowNode):
    NODE_NAME = "Image Generation"

    def __init__(self):
        super().__init__()

        # Basic inputs
        self.add_input("image_request")

        # Output - change to image_response to match our new node
        self.add_output("image_response")

    def execute(self, input_data):
        # Convert inputs to proper types
        prompt_data = input_data.get("prompt_data", {})
        request = input_data.get("image_request", None)
        if not request:
            return

        # TODO: Implement the actual image generation using the request
        # This would involve calling the appropriate backend service

        # For now, create a simple test image with the prompt text
        prompt = prompt_data.get("prompt", "Empty prompt")
        width = int(input_data.get("width", 512))
        height = int(input_data.get("height", 512))

        # Create a simple colored image for testing
        color = (
            random.randint(0, 255),
            random.randint(0, 255),
            random.randint(0, 255),
        )
        img = PIL.Image.new("RGB", (width, height), color)

        # Create and return an ImageResponse object
        response = ImageResponse(
            images=[img],  # List with our test image
            data={
                "prompt": prompt,
                "request": request,
            },  # Include request data
            nsfw_content_detected=False,
            active_rect=Rect(0, 0, width, height),
            is_outpaint=False,
        )

        # Return the ImageResponse in the image_response output
        return {
            "image_response": response,
            "_exec_triggered": self.EXEC_OUT_PORT_NAME,
        }
