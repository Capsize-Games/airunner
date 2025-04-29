from typing import Dict
import os
from typing import ClassVar

# PySide6 Imports for Video Playback
from PySide6.QtCore import QUrl, Qt
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QSizePolicy,
    QApplication,
)  # Added QApplication for standalone testing if needed
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtMultimediaWidgets import QVideoWidget

# Assuming these imports exist in your project structure
from airunner.enums import (
    SignalCode,
)  # May not be needed if not emitting signals
from airunner.gui.widgets.nodegraph.nodes.core.base_workflow_node import (
    BaseWorkflowNode,
)

# Assuming NodePropWidgetEnum might be needed if properties are added later
# from airunner.gui.widgets.nodegraph.nodes.art.image_request_node import (
#     NodePropWidgetEnum,
# )
from airunner.utils.application.get_logger import get_logger

# from airunner.settings import AIRUNNER_LOG_LEVEL # Assuming logger setup handles level


# --- Helper Widget for Video Playback ---


class VideoPlayerWidget(QWidget):
    """A simple QWidget to display and play a video file."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Video Playback")
        self.setGeometry(100, 100, 800, 600)  # x, y, width, height

        self._media_player = QMediaPlayer(self)
        self._video_widget = QVideoWidget(self)
        self._audio_output = QAudioOutput(self)  # Required for audio playback

        self._media_player.setVideoOutput(self._video_widget)
        self._media_player.setAudioOutput(self._audio_output)

        layout = QVBoxLayout(self)
        layout.addWidget(self._video_widget)
        self.setLayout(layout)

        self._video_widget.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )

        # Handle potential errors
        self._media_player.errorOccurred.connect(self._handle_error)

    def play_video(self, file_path: str):
        """Loads and plays the video from the given file path."""
        if not os.path.exists(file_path):
            print(
                f"Error: Video file not found at {file_path}"
            )  # Use logger ideally
            # Optionally display an error message in the widget
            return

        media_url = QUrl.fromLocalFile(file_path)
        self._media_player.setSource(media_url)
        self.setWindowTitle(f"Video Playback - {os.path.basename(file_path)}")
        print(f"Attempting to play: {file_path}")  # Use logger ideally
        self._media_player.play()

    def _handle_error(self, error: QMediaPlayer.Error, error_string: str):
        """Logs media player errors."""
        # Replace print with self.logger.error ideally if logger passed in
        print(f"MediaPlayer Error ({error}): {error_string}")
        print(f"Media source: {self._media_player.source().toString()}")

    def closeEvent(self, event):
        """Stops playback when the widget is closed."""
        self._media_player.stop()
        super().closeEvent(event)


# --- VideoNode Definition ---


def register_nodes(registry):
    """Register the VideoNode with the NodeGraph registry."""
    registry.register_node("Display", VideoNode)  # Changed category


class VideoNode(BaseWorkflowNode):
    """
    Node for displaying a video file provided via input path.

    This node takes a file path to an MP4 video and plays it in a
    separate Qt widget when executed.
    """

    __identifier__ = "VideoPlayer"  # Unique identifier
    NODE_NAME = "Video Player"  # Name displayed in the node graph UI

    # Class variables
    title: ClassVar[str] = "Video Player"  # Title shown in the node header
    type_name: ClassVar[str] = "video_player"  # Internal type name
    category: ClassVar[str] = "Display"  # Category for node organization

    def __init__(self):
        """Initialize the VideoNode."""
        super().__init__()
        self._setup_ports()
        self._setup_properties()
        self._video_widget = None  # To hold the reference to the player window

    def _setup_ports(self):
        """Set up the input and output ports for the node."""
        # Input port to receive the video file path
        self.add_input("video_path", display_name=True)

        # No output port needed for simple playback
        # self.add_output("output_data", display_name=True) # Example if output needed

    def _setup_properties(self):
        """Set up the configurable properties for the node."""
        # No specific properties needed for basic playback in this version.
        # Could add properties like "Auto Play", "Volume", "Loop", etc. later
        # Example:
        # self.create_property(
        #     "auto_play",
        #     True,
        #     widget_type=NodePropWidgetEnum.QCHECK_BOX.value,
        #     tab="settings",
        # )
        pass  # No properties for now

    def execute(self, input_data: Dict):
        """Execute the node to play the input video."""
        self.logger.info(f"Executing {self.title} node (ID: {self.id})")

        # Get the input video path
        # Assuming the framework connects the output of a previous node
        # to an input property with the same name as the input port.
        video_path = self.get_property("video_path")

        if not video_path or not isinstance(video_path, str):
            self.logger.error(
                "No valid video path provided to input 'video_path'"
            )
            # Emit error signal or update node status if your framework supports it
            return {"error": "No valid video path provided"}

        if not os.path.exists(video_path):
            self.logger.error(f"Video file not found at path: {video_path}")
            return {"error": f"Video file not found: {video_path}"}

        self.logger.info(f"Received video path: {video_path}")

        try:
            # Ensure QApplication instance exists (usually managed by the main app)
            # app = QApplication.instance()
            # if not app:
            #     # This should ideally not happen if running within a Qt app
            #     self.logger.warning("QApplication instance not found. Video playback might fail.")
            #     # app = QApplication([]) # Avoid creating multiple instances if possible

            # Close previous widget if it exists and node is re-executed
            if self._video_widget and self._video_widget.isVisible():
                self.logger.debug("Closing previous video player window.")
                self._video_widget.close()
                # Note: Depending on event loop timing, direct close might not immediately
                # destroy the widget. Setting to None ensures a new one is created.
                self._video_widget = None

            # Create and show the video player widget
            self.logger.debug("Creating new video player widget.")
            self._video_widget = VideoPlayerWidget()
            self._video_widget.play_video(video_path)
            self._video_widget.show()

            # Emit completion signal if necessary for your workflow
            # self.mediator.emit_signal(
            #     SignalCode.NODE_EXECUTION_COMPLETED_SIGNAL,
            #     {"node_id": self.id, "result": {"status": "Video playing"}}
            # )

            self.logger.info(f"Video player launched for: {video_path}")
            return {"status": f"Playing video: {os.path.basename(video_path)}"}

        except Exception as e:
            self.logger.exception(f"Error executing VideoNode: {e}")
            # Emit error signal or update node status
            return {"error": f"Failed to play video: {e}"}

    # --- Optional: Cleanup method ---
    # If your BaseWorkflowNode or framework supports cleanup when the node
    # is removed or the workflow closes, you can close the widget there.
    # def on_removed(self):
    #     """Called when the node is removed from the graph."""
    #     if self._video_widget:
    #         self._video_widget.close()
    #         self._video_widget = None
    #     super().on_removed() # Call base class method if it exists
