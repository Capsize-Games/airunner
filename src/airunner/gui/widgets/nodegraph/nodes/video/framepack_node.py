from typing import ClassVar

from airunner.enums import SignalCode
from airunner.gui.widgets.nodegraph.nodes.art.image_request_node import (
    NodePropWidgetEnum,
)
from airunner.gui.widgets.nodegraph.nodes.core.base_workflow_node import (
    BaseWorkflowNode,
)

from airunner.utils.application.get_logger import get_logger
from airunner.settings import AIRUNNER_LOG_LEVEL


def register_nodes(registry):
    """Register the FramePackNode with the NodeGraph registry."""
    registry.register_node("Video Generation", FramePackNode)


class FramePackNode(BaseWorkflowNode):
    """
    Node for generating videos using the FramePack library.

    This node provides a UI for configuring and generating videos from images
    using the FramePack library's motion model.
    """

    __identifier__ = "FramePack"
    NODE_NAME = "FramePack"

    # Class variables
    title: ClassVar[str] = "Video Generation"
    type_name: ClassVar[str] = "video_generation"
    category: ClassVar[str] = "Video"

    def __init__(self):
        """Initialize the FramePackNode."""
        super().__init__()
        self._setup_ports()
        self._setup_properties()

    def _setup_ports(self):
        """Set up the input and output ports for the node."""
        # Input ports
        self.add_input("image", display_name=True)

        # Output ports
        self.add_output("video", display_name=True)

    def _setup_properties(self):
        """Set up the configurable properties for the node."""
        # Basic properties
        self.add_text_input(
            name="prompt",
            label="Prompt",
            text="",
            placeholder_text="Enter prompt here",
            tooltip="",
            tab="settings",
        )

        self.add_text_input(
            name="negative_prompt",
            label="Negative Prompt",
            text="",
            placeholder_text="Enter negative prompt here",
            tooltip="",
            tab="settings",
        )

        # Advanced properties
        self.create_property(
            "duration",
            5.0,
            widget_type=NodePropWidgetEnum.QDOUBLESPIN_BOX.value,
            tab="settings",
        )
        self.create_property(
            "steps",
            20,
            widget_type=NodePropWidgetEnum.QSPIN_BOX.value,
            tab="settings",
        )
        self.create_property(
            "guidance_scale",
            4.0,
            widget_type=NodePropWidgetEnum.QDOUBLESPIN_BOX.value,
            tab="settings",
        )
        self.create_property(
            "cfg",
            7.5,
            widget_type=NodePropWidgetEnum.QDOUBLESPIN_BOX.value,
            tab="settings",
        )
        self.create_property(
            "seed",
            42,
            widget_type=NodePropWidgetEnum.QSPIN_BOX.value,
            tab="settings",
        )
        self.create_property(
            "use_random_seed",
            True,
            widget_type=NodePropWidgetEnum.QCHECK_BOX.value,
            tab="settings",
        )

    def execute(self, input_data=None):
        """Execute the node to generate a video."""
        self.logger.info(f"Executing {self.title} node")

        # Get the input image
        input_image = input_data.get("image", None) if input_data else None
        if input_image is None:
            self.logger.error("No input image provided")
            return {"error": "No input image provided"}

        # Get property values
        prompt = self.get_property("prompt")
        negative_prompt = self.get_property("negative_prompt")
        duration = self.get_property("duration")
        steps = self.get_property("steps")
        guidance_scale = self.get_property("guidance_scale")
        cfg = self.get_property("cfg")
        seed = self.get_property("seed")
        use_random_seed = self.get_property("use_random_seed")

        # Generate a random seed if requested
        if use_random_seed:
            import random

            seed = random.randint(0, 2147483647)

        # Prepare the data for the handler
        data = {
            "input_image": input_image,
            "prompt": prompt,
            "negative_prompt": negative_prompt,
            "duration": duration,
            "steps": steps,
            "guidance_scale": guidance_scale,
            "cfg": cfg,
            "seed": seed,
            "node_id": self.id,
        }

        # Emit signal to generate video
        self.mediator.emit_signal(SignalCode.VIDEO_GENERATE_SIGNAL, data)

        # Register for video generation signals
        self.register(
            SignalCode.VIDEO_GENERATED_SIGNAL, self._on_video_generated
        )
        self.register(
            SignalCode.VIDEO_PROGRESS_SIGNAL, self._on_video_progress
        )

        # Return a placeholder - actual result will be set when video is generated
        return {"status": "Video generation started"}

    def _on_video_generated(self, data):
        """Handle generated video data."""
        if data.get("node_id") == self.id:
            video_path = data.get("video_path")
            self.set_property("video", video_path)

            # Emit signal that execution is complete
            self.mediator.emit_signal(
                SignalCode.NODE_EXECUTION_COMPLETED_SIGNAL,
                {"node_id": self.id, "result": {"video": video_path}},
            )

    def _on_video_progress(self, data):
        """Handle progress updates during video generation."""
        if data.get("node_id") == self.id:
            progress = data.get("progress", 0)
            message = data.get("message", "")
            self.logger.info(
                f"Video generation progress: {progress}% - {message}"
            )

            # Update node status if supported
            # if hasattr(self, "set_status"):
            #     self.set_status(f"Generating: {progress}%")
