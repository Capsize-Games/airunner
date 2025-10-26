#!/usr/bin/env python3
"""
VoiceVisualizer Widget Component for PySide6 Projects
=====================================================

This module provides a clean VoiceVisualizer widget for integration into airunner.
Contains only the visualizer without GUI controls.

Usage:
    from airunner.components.voice_visualizer.gui.widgets.voice_visualizer_component import VoiceVisualizerComponent

    # In your PySide6 application:
    visualizer = VoiceVisualizerComponent()
    layout.addWidget(visualizer)
"""

import sys
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QSurfaceFormat

# Import the VoiceVisualizer wrapper
from airunner.components.voice_visualizer.gui.widgets.voice_visualizer_python import (
    VoiceVisualizerWidget as VoiceVisualizerPython,
)


class VoiceVisualizerComponent(QWidget):
    """
    A clean VoiceVisualizer component without GUI controls.

    Features:
    - Audio-reactive visualization
    - Hardware-accelerated rendering when available
    - Graceful fallback to software rendering
    """

    # Signals for external control if needed
    audio_levels_changed = Signal(float, float, float)  # bass, mid, treble
    fps_changed = Signal(float)

    def __init__(self, parent=None):
        super().__init__(parent)

        # Initialize the core visualizer
        self.visualizer = None
        self.init_visualizer()

        # Setup UI (just the visualizer, no controls)
        self.setup_ui()

    def init_visualizer(self):
        """Initialize the VoiceVisualizer widget"""
        try:
            # Ensure OpenGL context is available before creating widget
            if not self._verify_opengl_support():
                return

            # Create the visualizer
            self.visualizer = VoiceVisualizerPython()

            if not self.visualizer:
                return

            # Configure basic settings
            self.visualizer.set_audio_enabled(True)
            self.visualizer.set_target_fps(60)

            # Get available shaders and set the first one if available
            shaders = self.visualizer.get_available_shaders()
            if shaders and len(shaders) > 0:
                try:
                    self.visualizer.set_current_shader(shaders[0])
                except Exception:
                    # Continue without custom shader if setting fails
                    pass

        except Exception:
            # Fail silently to avoid console spam
            self.visualizer = None

    def _verify_opengl_support(self):
        """Verify OpenGL context is available"""
        try:
            from PySide6.QtOpenGLWidgets import QOpenGLWidget

            # Test creating a simple OpenGL widget
            test_widget = QOpenGLWidget()
            test_widget.deleteLater()
            return True
        except Exception:
            return False

    def setup_ui(self):
        """Setup the user interface - just the visualizer widget"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(
            0, 0, 0, 0
        )  # Remove margins for clean integration

        # Visualizer widget
        if self.visualizer and self.visualizer.widget:
            visualizer_widget = self.visualizer.widget
            visualizer_widget.setMinimumSize(200, 150)  # Smaller minimum size
            layout.addWidget(visualizer_widget)
        else:
            error_label = QLabel("❌ VoiceVisualizer failed to initialize")
            error_label.setStyleSheet(
                "color: red; font-weight: bold; padding: 20px; text-align: center;"
            )
            error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(error_label)

    # Public API for external control
    def set_audio_enabled(self, enabled: bool):
        """Enable/disable audio reactivity"""
        if self.visualizer:
            self.visualizer.set_audio_enabled(enabled)

    def set_target_fps(self, fps: int):
        """Set target framerate"""
        if self.visualizer:
            self.visualizer.set_target_fps(fps)

    def set_shader(self, shader_name: str):
        """Set the current shader"""
        if self.visualizer:
            self.visualizer.set_current_shader(shader_name)

    def get_available_shaders(self):
        """Get list of available shaders"""
        if self.visualizer:
            return self.visualizer.get_available_shaders()
        return []

    def get_audio_levels(self):
        """Get current audio levels as (bass, mid, treble) tuple"""
        if self.visualizer:
            return self.visualizer.get_audio_levels()
        return (0.0, 0.0, 0.0)

    def get_current_fps(self):
        """Get current rendering FPS"""
        if self.visualizer:
            return self.visualizer.get_current_fps()
        return 0.0


# For standalone testing
if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication, QMainWindow

    # Set up OpenGL format
    fmt = QSurfaceFormat()
    fmt.setVersion(3, 3)
    fmt.setProfile(QSurfaceFormat.OpenGLContextProfile.CoreProfile)
    QSurfaceFormat.setDefaultFormat(fmt)

    app = QApplication(sys.argv)

    window = QMainWindow()
    window.setWindowTitle("Clean VoiceVisualizer Component Demo")
    window.setGeometry(100, 100, 600, 400)

    # Create and set the visualizer component
    visualizer_component = VoiceVisualizerComponent()
    window.setCentralWidget(visualizer_component)

    window.show()

    sys.exit(app.exec())
