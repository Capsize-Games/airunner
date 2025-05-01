from typing import Dict
import os
from typing import ClassVar
import cv2
from PIL import Image
from PIL.ImageQt import ImageQt

# PySide6 Imports for Video Playback
from PySide6.QtCore import (
    QUrl,
    Qt,
    Signal,
    QTimer,
    QThread,
    QMutex,
    QWaitCondition,
)
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QSlider,
    QSizePolicy,
    QLabel,
)
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput, QVideoSink
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtGui import QPixmap

# NodeGraphQt imports
from NodeGraphQt import NodeBaseWidget, Port
from NodeGraphQt.constants import NodePropWidgetEnum

# Airunner imports
from airunner.gui.widgets.nodegraph.nodes.core.base_workflow_node import (
    BaseWorkflowNode,
)


class VideoFrameExtractor(QThread):
    """Worker thread to extract frames from video to improve performance."""

    frame_ready = Signal(object)

    def __init__(self):
        super().__init__()
        self.mutex = QMutex()
        self.condition = QWaitCondition()
        self.video_path = None
        self.percentage = 0.0
        self.cap = None
        self.running = False
        self.restart = False
        self.abort = False

    def extract_frame(self, video_path, percentage):
        """Request frame extraction with parameters."""
        self.mutex.lock()
        self.video_path = video_path
        self.percentage = percentage
        self.restart = True
        self.condition.wakeOne()
        self.mutex.unlock()

        # Start the thread if not already running
        if not self.isRunning():
            self.start()

    def run(self):
        """Thread main loop."""
        self.running = True

        while self.running:
            # Wait for work
            self.mutex.lock()
            if not self.restart and not self.abort:
                self.condition.wait(self.mutex)

            video_path = self.video_path
            percentage = self.percentage
            self.restart = False
            self.mutex.unlock()

            # Check for abort
            if self.abort:
                break

            # Process the frame extraction
            if video_path and os.path.exists(video_path):
                if not self.cap or self.cap.get(cv2.CAP_PROP_FPS) == 0:
                    # Initialize or reinitialize the capture
                    if self.cap:
                        self.cap.release()
                    self.cap = cv2.VideoCapture(video_path)

                if self.cap.isOpened():
                    # Get total frames
                    total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
                    if total_frames > 0:
                        target_frame = int(percentage * total_frames)

                        # Set position to the target frame
                        self.cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)

                        # Read the frame
                        success, frame = self.cap.read()
                        if success:
                            # Convert BGR to RGB
                            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

                            # Resize to 608x640
                            resized_frame = cv2.resize(rgb_frame, (608, 640))

                            # Convert to PIL Image
                            pil_img = Image.fromarray(resized_frame)

                            # Emit the frame
                            self.frame_ready.emit(pil_img)

    def stop(self):
        """Stop the thread."""
        self.mutex.lock()
        self.abort = True
        self.condition.wakeOne()
        self.mutex.unlock()

        self.wait()

        if self.cap and self.cap.isOpened():
            self.cap.release()


class VideoPlayerWidget(NodeBaseWidget):
    """Widget to display videos in a node graph with playback controls."""

    value_changed = Signal(str, object)
    path_changed_signal = Signal(str)

    def __init__(self, parent=None, name="video_player", label="Video Player"):
        super().__init__(parent, name, label)

        # Main container widget
        self.container = QWidget()
        main_layout = QVBoxLayout()
        self.container.setLayout(main_layout)

        # Video widget with video sink for better performance
        self._video_widget = QVideoWidget()
        self._video_widget.setMinimumSize(400, 300)
        self._video_widget.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Expanding
        )

        # Video sink for hardware acceleration
        self._video_sink = QVideoSink()

        # Media player and audio output
        self._media_player = QMediaPlayer()
        self._audio_output = QAudioOutput()
        self._media_player.setVideoOutput(self._video_widget)
        self._media_player.setAudioOutput(self._audio_output)
        self._media_player.setVideoSink(self._video_sink)

        # Current frame preview
        self.frame_preview = QLabel("No Frame")
        self.frame_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.frame_preview.setMinimumSize(200, 200)

        # Add video widget to layout
        main_layout.addWidget(self._video_widget)

        # Controls layout
        controls_layout = QHBoxLayout()

        # Play/Pause button
        self.play_button = QPushButton("Play")
        self.play_button.clicked.connect(self._toggle_play)

        # Timeline slider
        self.timeline_slider = QSlider(Qt.Orientation.Horizontal)
        self.timeline_slider.setRange(
            0, 1000
        )  # Use 0-1000 for percentage precision
        self.timeline_slider.valueChanged.connect(self._seek_video)
        self.timeline_slider.sliderReleased.connect(self._slider_released)

        # Add controls to layout
        controls_layout.addWidget(self.play_button)
        controls_layout.addWidget(self.timeline_slider)

        # Add controls to main layout
        main_layout.addLayout(controls_layout)
        main_layout.addWidget(self.frame_preview)

        # Set the container as our custom widget
        self.set_custom_widget(self.container)

        # Initialize state variables
        self._value = None
        self._video_path = None
        self._is_playing = False
        self._frame = None

        # Create frame extractor thread
        self._frame_extractor = VideoFrameExtractor()
        self._frame_extractor.frame_ready.connect(self._update_frame)

        # Timer for updating slider position during playback
        self._update_timer = QTimer()
        self._update_timer.setInterval(100)  # 100ms update interval
        self._update_timer.timeout.connect(self._update_timeline)

        # Connect media player signals
        self._media_player.playbackStateChanged.connect(
            self._handle_playback_state
        )
        self._media_player.errorOccurred.connect(self._handle_error)

    def _toggle_play(self):
        """Toggle play/pause state of the video"""
        if self._media_player.playbackState() == QMediaPlayer.PlayingState:
            self._media_player.pause()
            self.play_button.setText("Play")
            self._is_playing = False
            self._update_timer.stop()
        else:
            self._media_player.play()
            self.play_button.setText("Pause")
            self._is_playing = True
            self._update_timer.start()

    def _seek_video(self):
        """Seek the video based on slider position"""
        if not self._media_player.hasVideo():
            return

        percentage = self.timeline_slider.value() / 1000.0
        position = int(percentage * self._media_player.duration())
        self._media_player.setPosition(position)

        # Extract and show current frame using the worker thread
        self._frame_extractor.extract_frame(self._video_path, percentage)

    def _slider_released(self):
        """Handle slider release event"""
        percentage = self.timeline_slider.value() / 1000.0
        self._frame_extractor.extract_frame(self._video_path, percentage)

    def _update_timeline(self):
        """Update the slider position based on video progress"""
        if self._media_player.duration() > 0:
            percentage = (
                self._media_player.position() / self._media_player.duration()
            )
            self.timeline_slider.setValue(int(percentage * 1000))

    def _update_frame(self, pil_img):
        """Update the frame preview with the extracted frame"""
        if pil_img:
            # Convert to QImage for display
            qimage = ImageQt(pil_img)
            pixmap = QPixmap.fromImage(qimage)

            # Scale for preview
            preview_size = self.frame_preview.size()
            scaled_pixmap = pixmap.scaled(
                preview_size,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )

            # Display the frame
            self.frame_preview.setPixmap(scaled_pixmap)

            # Store the frame for output
            self._frame = pil_img

    def _handle_playback_state(self, state):
        """Handle media player state changes"""
        if state == QMediaPlayer.PlaybackState.PlayingState:
            self.play_button.setText("Pause")
            self._is_playing = True
            self._update_timer.start()
        else:
            self.play_button.setText("Play")
            self._is_playing = False
            self._update_timer.stop()

    def _handle_error(self, error, error_string):
        """Log media player errors"""
        print(f"MediaPlayer Error ({error}): {error_string}")
        self.frame_preview.setText(f"Error: {error_string}")

    def play_video(self, file_path):
        """Load and play a video file"""
        if not file_path or not os.path.exists(file_path):
            self.frame_preview.setText("Video file not found")
            return False

        self._video_path = file_path

        # Set up media player
        media_url = QUrl.fromLocalFile(file_path)
        self._media_player.setSource(media_url)

        # Extract the first frame
        self._frame_extractor.extract_frame(file_path, 0)

        return True

    def get_value(self):
        """Return the current frame"""
        return self._frame

    def set_value(self, value=None):
        """Required method for NodeGraphQt to restore widget state"""
        if isinstance(value, str) and os.path.exists(value):
            self.play_video(value)
        self._value = value
        self.value_changed.emit(self._name, value)

    def get_current_frame(self):
        """Get the currently displayed frame as a PIL Image"""
        return self._frame

    def set_path(self, path):
        """Set the video path and emit signal for node to react"""
        if path and os.path.exists(path):
            self.play_video(path)
            self.path_changed_signal.emit(path)

    def cleanup(self):
        """Clean up resources when widget is no longer needed"""
        if hasattr(self, "_frame_extractor") and self._frame_extractor:
            self._frame_extractor.stop()

        if self._media_player:
            self._media_player.stop()

        if self._update_timer.isActive():
            self._update_timer.stop()


class VideoNode(BaseWorkflowNode):
    """
    Node for displaying a video file and extracting frames at specific points.

    This node takes a file path to a video, plays it in the node,
    and allows extracting a specific frame to pass to the next node.
    """

    __identifier__ = "VideoPlayer"
    NODE_NAME = "Video Player"

    title: ClassVar[str] = "Video Player"
    type_name: ClassVar[str] = "video_player"
    category: ClassVar[str] = "Display"
    _input_ports = [
        dict(name="video_path", display_name=True),
    ]
    _output_ports = [
        dict(name="frame", display_name=True),
    ]
    _properties = [
        dict(
            name="video_path",
            value="",
            widget_type=NodePropWidgetEnum.QLINE_EDIT,
            tab="settings",
        ),
    ]

    def __init__(self):
        """Initialize the VideoNode."""
        super().__init__()

        # Create the video player widget
        self.video_widget = VideoPlayerWidget(self.view, name="video_player")
        self.add_custom_widget(self.video_widget)

        # Connect to path changes from widget
        self.video_widget.path_changed_signal.connect(
            self._on_widget_path_changed
        )

    def on_property_changed(self, prop_name):
        """Handle property changes in the node - called by NodeGraphQt."""
        if prop_name == "video_path":
            value = self.get_property("video_path")
            if value:
                self.video_widget.set_path(value)

    def _on_property_changed(self, prop_name, value):
        """Handle property changes in the node."""
        if prop_name == "video_path" and value:
            self.video_widget.set_path(value)

    def _on_widget_path_changed(self, path):
        """Handle path changes from the widget."""
        if path != self.get_property("video_path"):
            self.set_property("video_path", path)

    def on_input_connected(self, in_port: Port, out_port: Port):
        """Handle when an input port gets connected."""
        super().on_input_connected(in_port, out_port)

        # If video_path input is connected, try to get the path immediately
        if in_port.name() == "video_path":
            # Request the connected node to execute and get the output
            from_node = out_port.node()
            if from_node:
                value = from_node.execute({})
                path = value.get(out_port.name())
                if path and isinstance(path, str):
                    self.video_widget.set_path(path)

    def execute(self, input_data: Dict):
        """Execute the node to process the video."""
        self.logger.info(f"Executing {self.title} node (ID: {self.id})")

        # Get the input video path
        video_path = input_data.get("video_path") or self.get_property(
            "video_path"
        )

        if not video_path or not isinstance(video_path, str):
            self.logger.error("No valid video path provided")
            return {"frame": None, "error": "No valid video path provided"}

        if not os.path.exists(video_path):
            self.logger.error(f"Video file not found at path: {video_path}")
            return {
                "frame": None,
                "error": f"Video file not found: {video_path}",
            }

        # Load the video into the widget if not already loaded or if path changed
        if self.video_widget._video_path != video_path:
            success = self.video_widget.play_video(video_path)
            if not success:
                return {
                    "frame": None,
                    "error": f"Failed to load video: {video_path}",
                }

        # Extract the current frame
        frame = self.video_widget.get_current_frame()

        # Return the extracted frame (even if None)
        return {"frame": frame}

    def on_node_deleted(self):
        """Clean up when node is deleted."""
        if hasattr(self, "video_widget"):
            self.video_widget.cleanup()
        super().on_node_deleted()


def register_nodes(registry):
    """Register the VideoNode with the NodeGraph registry."""
    registry.register_node("Display", VideoNode)
