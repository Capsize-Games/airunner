from typing import ClassVar, Dict
import os

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
    """Register the MuseTalkNode with the NodeGraph registry."""
    registry.register_node("Video", MuseTalkNode)


class MuseTalkNode(BaseWorkflowNode):
    """
    Node for lip-syncing videos using the MuseTalk model.

    This node provides a UI for configuring and generating lip-synced videos
    by applying audio to video inputs using MuseTalk's AI-driven lip movement synthesis.
    """

    __identifier__ = "MuseTalk"
    NODE_NAME = "MuseTalk Lip Sync"

    # Class variables
    title: ClassVar[str] = "MuseTalk Lip Sync"
    type_name: ClassVar[str] = "musetalk_lip_sync"
    category: ClassVar[str] = "Video"

    def __init__(self):
        """Initialize the MuseTalkNode."""
        self.signal_handlers = {
            SignalCode.VIDEO_GENERATED_SIGNAL: self._on_video_generated,
            SignalCode.VIDEO_PROGRESS_SIGNAL: self._on_video_progress,
        }
        self._pending_request = False
        super().__init__()

        self._setup_ports()
        self._setup_properties()

    def _setup_ports(self):
        """Set up the input and output ports for the node."""
        # Input ports
        self.add_input("video_in", display_name=True)
        self.add_input("audio_in", display_name=True)

        # Output ports
        self.add_output("video_out", display_name=True)

    def _setup_properties(self):
        """Set up the configurable properties for the node."""
        # Add properties that allow the user to configure the lip-sync process
        self.create_property(
            "output_path",
            "",
            widget_type=NodePropWidgetEnum.FILE_SAVE.value,
            tab="Output",
        )

        # Add a face center adjustment property (optional)
        self.create_property(
            "face_center_x",
            0.5,
            widget_type=NodePropWidgetEnum.SLIDER.value,
            tab="Advanced",
        )

        self.create_property(
            "face_center_y",
            0.5,
            widget_type=NodePropWidgetEnum.SLIDER.value,
            tab="Advanced",
        )

        # Add version selection property
        self.create_property(
            "version",
            "v1.5",
            widget_type=NodePropWidgetEnum.QCOMBO_BOX.value,
            items=["v1.5", "v1.0"],
            tab="Advanced",
        )

    def execute(self, input_data: Dict):
        """
        Execute the lip-sync generation using MuseTalk.

        Args:
            input_data (Dict): Input data containing:
                - video_in: Path to the input video file
                - audio_in: Path to the input audio file

        Returns:
            Dict: Output data containing:
                - video_out: Path to the generated lip-synced video file
        """
        self.logger.info(
            f"MuseTalkNode execute called with inputs: {input_data}"
        )

        if self._pending_request:
            self.logger.warning(
                "Ignoring request, a lip-sync generation is already pending"
            )
            return {"_exec_triggered": self.EXEC_OUT_PORT_NAME}

        # Get video and audio paths from input_data
        video_path = input_data.get("video_in")
        audio_path = input_data.get("audio_in")

        # Validate inputs
        if not video_path:
            self.logger.error("No video input provided")
            self.emit_signal(
                SignalCode.APPLICATION_STATUS_ERROR_SIGNAL,
                "Lip-sync failed: No video input provided",
            )
            return {"_exec_triggered": self.EXEC_OUT_PORT_NAME}

        if not audio_path:
            self.logger.error("No audio input provided")
            self.emit_signal(
                SignalCode.APPLICATION_STATUS_ERROR_SIGNAL,
                "Lip-sync failed: No audio input provided",
            )
            return {"_exec_triggered": self.EXEC_OUT_PORT_NAME}

        # Get configuration from properties
        output_path = self.get_property("output_path")
        face_center_x = self.get_property("face_center_x")
        face_center_y = self.get_property("face_center_y")
        version = self.get_property("version")

        # Configure the request data
        request_data = {
            "video_path": video_path,
            "audio_path": audio_path,
            "face_center_x": face_center_x,
            "face_center_y": face_center_y,
            "version": version,
        }

        # Add output path if specified
        if output_path:
            request_data["output_path"] = output_path

        self._pending_request = True

        # Send signal to generate lip-synced video
        self.logger.info(
            f"Sending lip-sync generation request: {request_data}"
        )
        self.emit_signal(
            SignalCode.MUSETALK_GENERATE_SIGNAL,
            request_data,
        )

        self.emit_signal(
            SignalCode.APPLICATION_STATUS_INFO_SIGNAL,
            "Lip-sync generation started...",
        )

        # Return an empty dictionary since we don't have results yet
        # The actual results will be returned via the callback
        return {"_exec_triggered": self.EXEC_OUT_PORT_NAME}

    def _on_video_generated(self, data):
        """Handle generated video data.

        Args:
            data (Dict): Dictionary containing:
                - path: Path to the generated lip-synced video
        """
        self.logger.info(f"Lip-sync generation completed: {data}")
        self._pending_request = False

        # Extract the output path from the data
        output_path = data.get("path")

        if output_path and os.path.exists(output_path):
            # Set the output port value
            self.set_output("video_out", output_path)

            # Emit signals to update UI
            self.emit_signal(
                SignalCode.NODE_OUTPUT_UPDATED,
                {
                    "node_id": self.id(),
                    "port_name": "video_out",
                    "value": output_path,
                },
            )

            self.emit_signal(
                SignalCode.APPLICATION_STATUS_SUCCESS_SIGNAL,
                f"Lip-sync generation completed: {output_path}",
            )
        else:
            self.logger.error(f"Generated video file not found: {output_path}")
            self.emit_signal(
                SignalCode.APPLICATION_STATUS_ERROR_SIGNAL,
                "Lip-sync generation failed: Output file not found",
            )

    def _on_video_progress(self, data):
        """Handle progress updates during lip-sync generation.

        Args:
            data (Dict): Dictionary containing:
                - percent: Progress percentage (0-100)
                - message: Status message
                - frame (optional): Preview frame image
        """
        percent = data.get("percent", 0)
        message = data.get("message", "Processing...")

        # Update node status with progress
        self.set_property("_progress", percent)

        # Update progress in UI
        progress_text = f"MuseTalk: {percent}% - {message}"
        self.set_property("_status", progress_text)

        # Emit signal to show progress in application status bar
        if percent % 5 == 0:  # Limit updates to every 5%
            self.emit_signal(
                SignalCode.APPLICATION_STATUS_INFO_SIGNAL,
                progress_text,
            )

        # If the data includes a preview frame, we could display it
        # This would require additional UI components specific to this node
