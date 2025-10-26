"""
Python bindings for VoiceVisualizer AudioReactiveWidget

This module provides Python access to the AudioReactiveWidget C++ class
through a shared library interface.

Requirements:
    - PySide6 with Qt 6.9+
    - libvoicevisualizer_widget.so (must be in same directory as this file)
    - NVIDIA proprietary drivers for hardware acceleration
    - OpenGL 3.3+ support
    - Linux with PulseAudio for audio capture

Usage:
    from voice_visualizer_python import VoiceVisualizerWidget

    # Create widget
    visualizer = VoiceVisualizerWidget()

    # Add to your PySide6 layout
    layout.addWidget(visualizer.widget)

    # Configure
    visualizer.set_audio_enabled(True)
    visualizer.set_target_fps(60)

Author: VoiceVisualizer Project
Version: 1.0.0
"""

__version__ = "1.0.0"
__author__ = "VoiceVisualizer Project"

import ctypes
import os
from ctypes import c_void_p, c_char_p, c_int, c_float, POINTER
from PySide6.QtWidgets import QWidget
from PySide6.QtOpenGLWidgets import QOpenGLWidget
import shiboken6


class VoiceVisualizerWidget:
    """Python wrapper for the AudioReactiveWidget C++ class"""

    def __init__(self, parent=None, library_path=None):
        """
        Initialize the VoiceVisualizer widget

        Args:
            parent: Parent QWidget (optional)
            library_path: Path to libvoicevisualizer_widget.so (optional, will search common paths)
        """
        self._load_library(library_path)
        self._setup_function_signatures()

        # Get parent pointer for C interface
        parent_ptr = None
        if parent is not None:
            parent_ptr = shiboken6.getCppPointer(parent)[0]

        # Create the C++ widget
        self._c_widget = self._lib.create_audio_reactive_widget(parent_ptr)
        if not self._c_widget:
            raise RuntimeError("Failed to create AudioReactiveWidget")

        # Get the Qt widget pointer and create Python wrapper
        qt_widget_ptr = self._lib.get_qt_widget(self._c_widget)

        # Try QOpenGLWidget with proper error handling for platform compatibility
        try:
            self._qt_widget = shiboken6.wrapInstance(
                qt_widget_ptr, QOpenGLWidget
            )
            print("✓ Successfully created QOpenGLWidget")
        except Exception as e:
            print(f"⚠ Failed to create QOpenGLWidget: {e}")
            print("  This may be due to Wayland/OpenGL compatibility issues")
            # Fall back to regular QWidget
            self._qt_widget = shiboken6.wrapInstance(qt_widget_ptr, QWidget)
            print("✓ Using QWidget fallback (software rendering)")

    def _load_library(self, library_path):
        """Load the shared library"""
        # Set up library path to use PySide6's Qt libraries first
        self._setup_library_path()

        if library_path and os.path.exists(library_path):
            try:
                self._lib = ctypes.CDLL(library_path)
                print(f"✓ Successfully loaded library from: {library_path}")
                return
            except OSError as e:
                raise RuntimeError(
                    f"Failed to load specified library '{library_path}': {e}"
                )

        # Get the directory where this Python file is located
        current_dir = os.path.dirname(os.path.abspath(__file__))

        # Production search paths - look for library in same directory first
        search_paths = [
            os.path.join(
                current_dir, "libvoicevisualizer_widget.so"
            ),  # Same directory as this file
            os.path.join(
                current_dir, "lib", "libvoicevisualizer_widget.so"
            ),  # lib subdirectory
            "./libvoicevisualizer_widget.so",  # Current working directory
            "/usr/local/lib/libvoicevisualizer_widget.so",  # System-wide install
            "/usr/lib/libvoicevisualizer_widget.so",  # System library
        ]

        self._lib = None
        load_errors = []

        for path in search_paths:
            if os.path.exists(path):
                try:
                    self._lib = ctypes.CDLL(path)
                    print(f"✓ Successfully loaded library from: {path}")
                    return
                except OSError as e:
                    load_errors.append(f"{path}: {e}")
                    continue

        # If we get here, library wasn't found
        error_details = "\n".join([f"  {err}" for err in load_errors])
        raise RuntimeError(
            f"Could not find or load libvoicevisualizer_widget.so!\n"
            f"Searched in:\n"
            + "\n".join([f"  {path}" for path in search_paths])
            + "\n"
            f"Make sure 'libvoicevisualizer_widget.so' is in the same directory as this Python file.\n"
            f"Load errors:\n{error_details}"
        )

    def _setup_library_path(self):
        """Set up library path to use PySide6's Qt libraries"""
        try:
            import PySide6

            pyside6_qt_lib_path = os.path.join(
                os.path.dirname(PySide6.__file__), "Qt", "lib"
            )

            if os.path.exists(pyside6_qt_lib_path):
                # Add PySide6's Qt lib path to the beginning of LD_LIBRARY_PATH
                current_ld_path = os.environ.get("LD_LIBRARY_PATH", "")
                if pyside6_qt_lib_path not in current_ld_path:
                    new_ld_path = (
                        f"{pyside6_qt_lib_path}:{current_ld_path}".rstrip(":")
                    )
                    os.environ["LD_LIBRARY_PATH"] = new_ld_path
                    print(
                        f"✓ Updated LD_LIBRARY_PATH to use PySide6 Qt libraries: {pyside6_qt_lib_path}"
                    )

                return True

        except ImportError:
            # PySide6 not available, continue with system Qt
            print(
                "⚠ Warning: PySide6 not available, using system Qt libraries"
            )
        except Exception as e:
            # Handle other potential errors gracefully
            print(f"⚠ Warning: Could not set up PySide6 library path: {e}")

        return False

    def _setup_function_signatures(self):
        """Setup C function signatures"""
        # Widget lifecycle
        self._lib.create_audio_reactive_widget.argtypes = [c_void_p]
        self._lib.create_audio_reactive_widget.restype = c_void_p

        self._lib.destroy_audio_reactive_widget.argtypes = [c_void_p]
        self._lib.destroy_audio_reactive_widget.restype = None

        self._lib.get_qt_widget.argtypes = [c_void_p]
        self._lib.get_qt_widget.restype = c_void_p

        # Widget properties
        self._lib.set_audio_enabled.argtypes = [c_void_p, c_int]
        self._lib.set_audio_enabled.restype = None

        self._lib.set_target_fps.argtypes = [c_void_p, c_int]
        self._lib.set_target_fps.restype = None

        self._lib.set_current_shader.argtypes = [c_void_p, c_char_p]
        self._lib.set_current_shader.restype = None

        # Audio levels
        self._lib.get_audio_levels.argtypes = [
            c_void_p,
            POINTER(c_float),
            POINTER(c_float),
            POINTER(c_float),
        ]
        self._lib.get_audio_levels.restype = None

        self._lib.get_current_fps.argtypes = [c_void_p]
        self._lib.get_current_fps.restype = c_float

        # Shader management
        self._lib.get_shader_count.argtypes = [c_void_p]
        self._lib.get_shader_count.restype = c_int

        self._lib.get_shader_name.argtypes = [c_void_p, c_int]
        self._lib.get_shader_name.restype = c_char_p

        # Shader uniform setting
        self._lib.set_shader_uniform_float.argtypes = [
            c_void_p,
            c_char_p,
            c_float,
        ]
        self._lib.set_shader_uniform_float.restype = None

        self._lib.set_shader_uniform_vec3.argtypes = [
            c_void_p,
            c_char_p,
            c_float,
            c_float,
            c_float,
        ]
        self._lib.set_shader_uniform_vec3.restype = None

        self._lib.get_shader_uniform_float.argtypes = [
            c_void_p,
            c_char_p,
            POINTER(c_float),
        ]
        self._lib.get_shader_uniform_float.restype = c_int

        self._lib.is_shader_program_active.argtypes = [c_void_p]
        self._lib.is_shader_program_active.restype = c_int

        # Post-processing
        self._lib.enable_post_processing_effect.argtypes = [
            c_void_p,
            c_char_p,
            c_int,
        ]
        self._lib.enable_post_processing_effect.restype = None

        self._lib.set_post_processing_uniform.argtypes = [
            c_void_p,
            c_char_p,
            c_char_p,
            c_float,
        ]
        self._lib.set_post_processing_uniform.restype = None

    def __del__(self):
        """Cleanup when object is destroyed"""
        if hasattr(self, "_c_widget") and self._c_widget:
            self._lib.destroy_audio_reactive_widget(self._c_widget)

    @property
    def widget(self):
        """Get the QWidget instance for embedding in Qt applications"""
        return self._qt_widget

    # Widget control methods
    def set_audio_enabled(self, enabled):
        """Enable/disable audio reactivity"""
        self._lib.set_audio_enabled(self._c_widget, 1 if enabled else 0)

    def set_target_fps(self, fps):
        """Set target framerate (30-240)"""
        self._lib.set_target_fps(self._c_widget, int(fps))

    def set_current_shader(self, shader_name):
        """Set the current visualization shader"""
        self._lib.set_current_shader(
            self._c_widget, shader_name.encode("utf-8")
        )

    def get_audio_levels(self):
        """Get current audio levels as (bass, mid, treble) tuple"""
        bass = c_float()
        mid = c_float()
        treble = c_float()
        self._lib.get_audio_levels(self._c_widget, bass, mid, treble)
        return (bass.value, mid.value, treble.value)

    def get_current_fps(self):
        """Get current rendering FPS"""
        return self._lib.get_current_fps(self._c_widget)

    def get_available_shaders(self):
        """Get list of available shader names"""
        count = self._lib.get_shader_count(self._c_widget)
        shaders = []
        for i in range(count):
            name_ptr = self._lib.get_shader_name(self._c_widget, i)
            if name_ptr:
                shaders.append(name_ptr.decode("utf-8"))
        return shaders

    def set_shader_uniform_float(self, uniform_name, value):
        """Set a float shader uniform value"""
        self._lib.set_shader_uniform_float(
            self._c_widget, uniform_name.encode("utf-8"), float(value)
        )

    def set_shader_uniform_vec3(self, uniform_name, r, g, b):
        """Set a vec3 shader uniform value (RGB)"""
        self._lib.set_shader_uniform_vec3(
            self._c_widget,
            uniform_name.encode("utf-8"),
            float(r),
            float(g),
            float(b),
        )

    def get_shader_uniform_float(self, uniform_name):
        """Get a float shader uniform value"""
        value = c_float()
        success = self._lib.get_shader_uniform_float(
            self._c_widget, uniform_name.encode("utf-8"), value
        )
        return value.value if success else None

    def is_shader_program_active(self):
        """Check if a shader program is currently active and ready for uniform setting"""
        return bool(self._lib.is_shader_program_active(self._c_widget))

    def enable_post_processing_effect(self, effect_name, enabled):
        """Enable/disable a post-processing effect"""
        self._lib.enable_post_processing_effect(
            self._c_widget, effect_name.encode("utf-8"), 1 if enabled else 0
        )

    def set_post_processing_uniform(self, effect_name, uniform_name, value):
        """Set a post-processing effect uniform value"""
        self._lib.set_post_processing_uniform(
            self._c_widget,
            effect_name.encode("utf-8"),
            uniform_name.encode("utf-8"),
            float(value),
        )


# Convenience function for creating widgets
def create_voice_visualizer_widget(parent=None, library_path=None):
    """
    Create a VoiceVisualizer widget

    Args:
        parent: Parent QWidget (optional)
        library_path: Path to the shared library (optional)

    Returns:
        VoiceVisualizerWidget instance
    """
    return VoiceVisualizerWidget(parent, library_path)
