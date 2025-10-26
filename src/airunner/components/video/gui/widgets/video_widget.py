"""
Video widget for video generation and playback.

Provides UI for generating videos using various models (HunyuanVideo, CogVideoX, etc.)
with real-time preview, timeline controls, and export functionality.
"""

from typing import Optional, List
import numpy as np
from PIL import Image

from PySide6.QtCore import Qt, QTimer, Slot
from PySide6.QtWidgets import (
    QFileDialog,
    QMessageBox,
    QGraphicsScene,
)
from PySide6.QtGui import QImage, QPixmap

from airunner.components.application.gui.widgets.base_widget import BaseWidget
from airunner.components.video.gui.widgets.templates.video_widget_ui import (
    Ui_video_widget,
)
from airunner.enums import SignalCode


class VideoWidget(BaseWidget):
    """
    Main video generation widget.

    Handles:
    - Video model selection
    - Prompt input and generation parameters
    - Source image selection for I2V
    - Video preview and playback
    - Timeline scrubbing
    - Progress monitoring
    - Video export
    """

    widget_class_ = Ui_video_widget

    def __init__(self, *args, **kwargs):
        """Initialize the video widget."""
        # Initialize state variables BEFORE super().__init__()
        self._current_video_frames: List[np.ndarray] = []
        self._current_frame_index: int = 0
        self._is_playing: bool = False
        self._source_image_path: Optional[str] = None
        self._generating: bool = False
        self._playback_timer = None

        # Signal handlers
        self.signal_handlers = {
            SignalCode.VIDEO_PROGRESS_SIGNAL: self.on_video_progress,
            SignalCode.VIDEO_FRAME_UPDATE_SIGNAL: self.on_frame_update,
            SignalCode.VIDEO_GENERATED_SIGNAL: self.on_video_generated,
            SignalCode.VIDEO_GENERATION_FAILED_SIGNAL: self.on_generation_failed,
        }

        # Call parent constructor
        super().__init__(*args, **kwargs)

    def initialize_ui(self) -> None:
        """Initialize UI components after widget setup."""
        try:
            super().initialize_ui()
        except Exception as e:
            self.logger.error(f"VideoWidget UI initialization failed: {e}")
            return

        try:
            self._setup_playback_timer()
            self._update_ui_state()
        except Exception as e:
            self.logger.error(
                f"VideoWidget component initialization failed: {e}"
            )

    def _setup_playback_timer(self) -> None:
        """Set up the playback timer."""
        self._playback_timer = QTimer(self)
        self._playback_timer.timeout.connect(self._advance_frame)

    def _update_ui_state(self):
        """Update UI element states based on current state."""
        if not hasattr(self, "ui") or self.ui is None:
            return

        # Enable/disable based on generation state
        is_generating = self._generating
        self.ui.btn_generate.setEnabled(not is_generating)
        self.ui.btn_cancel.setEnabled(is_generating)
        self.ui.model_selector.setEnabled(not is_generating)

        # Enable/disable based on img2vid checkbox
        is_img2vid = self.ui.checkbox_img2vid.isChecked()
        self.ui.label_source_image.setEnabled(is_img2vid)
        self.ui.lineedit_source_path.setEnabled(is_img2vid)
        self.ui.btn_browse_source.setEnabled(is_img2vid)
        self.ui.btn_clear_source.setEnabled(is_img2vid)

        # Enable/disable playback controls based on video availability
        has_video = len(self._current_video_frames) > 0
        self.ui.btn_play.setEnabled(has_video and not self._is_playing)
        self.ui.btn_pause.setEnabled(has_video and self._is_playing)
        self.ui.btn_stop.setEnabled(has_video)
        self.ui.btn_prev_frame.setEnabled(has_video)
        self.ui.btn_next_frame.setEnabled(has_video)
        self.ui.btn_export.setEnabled(has_video)
        self.ui.timeline_slider.setEnabled(has_video)

    # ===== Signal Handlers =====

    @Slot(dict)
    def on_video_progress(self, data: dict):
        """Handle video generation progress updates."""
        progress = data.get("progress", 0)
        message = data.get("message", "Generating...")

        self.ui.progress_bar.setValue(progress)
        self.ui.progress_bar.setFormat(f"%p% - {message}")

    @Slot(dict)
    def on_frame_update(self, data: dict):
        """Handle frame preview updates during generation."""
        frame = data.get("frame")
        if frame is not None:
            self._display_frame(frame)

    @Slot(dict)
    def on_video_generated(self, data: dict):
        """Handle successful video generation completion."""
        self._generating = False
        self.ui.progress_bar.setValue(100)
        self.ui.progress_bar.setFormat("Complete!")

        # Load generated video
        output_path = data.get("output_path")
        if output_path:
            self._load_video(output_path)

        self._update_ui_state()

        QMessageBox.information(
            self,
            "Video Generated",
            f"Video generated successfully!\n\n{output_path}",
        )

    @Slot(dict)
    def on_generation_failed(self, data: dict):
        """Handle video generation failure."""
        self._generating = False
        self.ui.progress_bar.setValue(0)
        self.ui.progress_bar.setFormat("Failed")
        self._update_ui_state()

        error = data.get("error", "Unknown error")
        QMessageBox.critical(
            self,
            "Generation Failed",
            f"Video generation failed:\n\n{error}",
        )

    # ===== UI Event Handlers (Auto-connected via @Slot naming convention) =====

    @Slot()
    def on_model_selector_currentIndexChanged(self):
        """Handle video model selection change (auto-connected)."""
        model_name = self.ui.model_selector.currentText()
        self.logger.info(f"Video model changed to: {model_name}")

        # Update frame limits based on model
        if "HunyuanVideo" in model_name:
            self.ui.spinbox_frames.setMaximum(513)
        elif "CogVideoX" in model_name:
            self.ui.spinbox_frames.setMaximum(129)
        elif "AnimateDiff" in model_name:
            self.ui.spinbox_frames.setMaximum(256)

    @Slot()
    def on_btn_generate_clicked(self) -> None:
        """Handle generate button click (auto-connected)."""
        # Validate inputs
        prompt = self.ui.prompt_input.toPlainText().strip()
        if not prompt:
            QMessageBox.warning(
                self,
                "Missing Prompt",
                "Please enter a prompt for video generation.",
            )
            return

        # Check for source image if img2vid is enabled
        is_img2vid = self.ui.checkbox_img2vid.isChecked()
        if is_img2vid and not self._source_image_path:
            QMessageBox.warning(
                self,
                "Missing Source Image",
                "Please select a source image for image-to-video generation.",
            )
            return

        # Gather parameters
        negative_prompt = self.ui.negative_prompt_input.toPlainText().strip()
        steps = self.ui.spinbox_steps.value()
        cfg_scale = self.ui.spinbox_cfg.value()
        num_frames = self.ui.spinbox_frames.value()
        fps = self.ui.spinbox_fps.value()
        seed = self.ui.spinbox_seed.value()
        if seed == -1:
            seed = None

        # Load source image
        init_image = None
        if is_img2vid and self._source_image_path:
            try:
                init_image = Image.open(self._source_image_path)
            except Exception as e:
                self.logger.error(f"Failed to load source image: {e}")
                QMessageBox.critical(
                    self,
                    "Image Load Error",
                    f"Failed to load source image:\n\n{e}",
                )
                return

        # Start generation
        self._generating = True
        self.ui.progress_bar.setValue(0)
        self.ui.progress_bar.setFormat("Starting generation...")
        self._update_ui_state()

        # Emit generation signal
        self.emit_signal(
            SignalCode.VIDEO_GENERATE_SIGNAL,
            {
                "prompt": prompt,
                "negative_prompt": negative_prompt,
                "init_image": init_image,
                "num_frames": num_frames,
                "fps": fps,
                "steps": steps,
                "cfg_scale": cfg_scale,
                "seed": seed,
            },
        )

    @Slot()
    def on_btn_cancel_clicked(self):
        """Handle cancel button click (auto-connected)."""
        self.emit_signal(SignalCode.INTERRUPT_VIDEO_GENERATION_SIGNAL, {})
        self._generating = False
        self.ui.progress_bar.setFormat("Cancelled")
        self._update_ui_state()

    @Slot(bool)
    def on_checkbox_img2vid_toggled(self, checked: bool):
        """Handle image-to-video checkbox toggle (auto-connected)."""
        self._update_ui_state()

    @Slot()
    def on_btn_browse_source_clicked(self):
        """Handle browse source image button click (auto-connected)."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Source Image",
            "",
            "Images (*.png *.jpg *.jpeg *.bmp *.webp);;All Files (*)",
        )

        if file_path:
            self._source_image_path = file_path
            self.ui.lineedit_source_path.setText(file_path)

    @Slot()
    def on_btn_clear_source_clicked(self):
        """Handle clear source image button click (auto-connected)."""
        self._source_image_path = None
        self.ui.lineedit_source_path.clear()

    @Slot()
    def on_btn_play_clicked(self) -> None:
        """Handle play button click (auto-connected)."""
        if not self._current_video_frames or not self._playback_timer:
            return

        self._is_playing = True
        fps = self.ui.spinbox_fps.value()
        self._playback_timer.start(int(1000 / fps))
        self._update_ui_state()

    @Slot()
    def on_btn_pause_clicked(self) -> None:
        """Handle pause button click (auto-connected)."""
        if not self._playback_timer:
            return

        self._is_playing = False
        self._playback_timer.stop()
        self._update_ui_state()

    @Slot()
    def on_btn_stop_clicked(self) -> None:
        """Handle stop button click (auto-connected)."""
        if not self._playback_timer:
            return

        self._is_playing = False
        self._playback_timer.stop()
        self._current_frame_index = 0
        self._update_frame_display()
        self._update_ui_state()

    @Slot()
    def on_btn_prev_frame_clicked(self):
        """Handle previous frame button click (auto-connected)."""
        if self._current_frame_index > 0:
            self._current_frame_index -= 1
            self._update_frame_display()

    @Slot()
    def on_btn_next_frame_clicked(self):
        """Handle next frame button click (auto-connected)."""
        if self._current_frame_index < len(self._current_video_frames) - 1:
            self._current_frame_index += 1
            self._update_frame_display()

    @Slot(int)
    def on_timeline_slider_valueChanged(self, value: int):
        """Handle timeline slider change (auto-connected)."""
        if 0 <= value < len(self._current_video_frames):
            self._current_frame_index = value
            self._update_frame_display()

    @Slot()
    def on_btn_export_clicked(self) -> None:
        """Handle export button click (auto-connected)."""
        if not self._current_video_frames:
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Video",
            "",
            "MP4 Video (*.mp4);;WebM Video (*.webm);;All Files (*)",
        )

        if file_path:
            # Emit export signal
            self.emit_signal(
                SignalCode.VIDEO_EXPORT_SIGNAL,
                {
                    "frames": self._current_video_frames,
                    "output_path": file_path,
                    "fps": self.ui.spinbox_fps.value(),
                },
            )

    @Slot()
    def on_btn_model_settings_clicked(self):
        """Handle model settings button click (auto-connected)."""
        # TODO: Open model settings dialog
        self.logger.info("Model settings clicked (not implemented)")

    # ===== Helper Methods =====

    def _advance_frame(self):
        """Advance to next frame during playback."""
        if not self._current_video_frames:
            self.on_btn_stop_clicked()
            return

        self._current_frame_index += 1
        if self._current_frame_index >= len(self._current_video_frames):
            # Loop playback
            self._current_frame_index = 0

        self._update_frame_display()

    def _update_frame_display(self):
        """Update the preview with current frame."""
        if not self._current_video_frames or self._current_frame_index >= len(
            self._current_video_frames
        ):
            return

        frame = self._current_video_frames[self._current_frame_index]
        self._display_frame(frame)

        # Update timeline slider
        self.ui.timeline_slider.blockSignals(True)
        self.ui.timeline_slider.setValue(self._current_frame_index)
        self.ui.timeline_slider.blockSignals(False)

        # Update timecode
        fps = self.ui.spinbox_fps.value()
        current_time = self._current_frame_index / fps
        total_time = len(self._current_video_frames) / fps
        self.ui.label_timecode.setText(
            f"{current_time:.2f}s / {total_time:.2f}s"
        )

    def _display_frame(self, frame: np.ndarray):
        """Display a frame in the preview area."""
        # Convert numpy array to QImage
        height, width, channels = frame.shape
        bytes_per_line = channels * width

        qimage = QImage(
            frame.data,
            width,
            height,
            bytes_per_line,
            QImage.Format_RGB888,
        )

        # Convert to pixmap and display
        pixmap = QPixmap.fromImage(qimage)

        # Scale to fit preview
        scene = self.ui.video_preview.scene()
        if scene is None:
            scene = QGraphicsScene()
            self.ui.video_preview.setScene(scene)

        scene.clear()
        scene.addPixmap(pixmap)
        self.ui.video_preview.fitInView(scene.sceneRect(), Qt.KeepAspectRatio)

    def _load_video(self, video_path: str):
        """Load video frames from file."""
        # TODO: Implement video loading via FFmpeg/OpenCV
        # For now, just log
        self.logger.info(f"Loading video from: {video_path}")

        # Placeholder: In a real implementation, we would:
        # 1. Use ffmpeg or opencv to extract frames
        # 2. Store frames in self._current_video_frames
        # 3. Update timeline slider range
        # 4. Display first frame

        # Update timeline
        if self._current_video_frames:
            self.ui.timeline_slider.setRange(
                0, len(self._current_video_frames) - 1
            )
            self._current_frame_index = 0
            self._update_frame_display()

        self._update_ui_state()
