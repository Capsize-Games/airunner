# VoiceVisualizer Component

This directory contains the VoiceVisualizer widget integration for AI Runner.

## Files

- `voice_visualizer_python.py` - Python bindings for the C++ AudioReactiveWidget
- `voice_visualizer_component.py` - Clean PySide6 component (visualizer only, no controls)
- `voice_visualizer_component_original.py` - Original component with full GUI controls (backup)
- `libvoicevisualizer_widget.so` - Compiled C++ shared library

## Component Features

The `VoiceVisualizerComponent` is a clean widget that provides:

- **Audio-reactive visualization** - Real-time visualization responding to audio input
- **Hardware acceleration** - Uses OpenGL when available, falls back to software rendering
- **Wayland compatibility** - Handles Wayland/X11 differences automatically
- **Clean integration** - No GUI controls, just the visualizer for embedding in airunner

## Usage

```python
from airunner.components.voice_visualizer.gui.widgets.voice_visualizer_component import VoiceVisualizerComponent

# Create the component
visualizer = VoiceVisualizerComponent()

# Add to your layout
layout.addWidget(visualizer)

# Optional: Control programmatically
visualizer.set_audio_enabled(True)
visualizer.set_target_fps(60)
```

## API Methods

- `set_audio_enabled(enabled: bool)` - Enable/disable audio reactivity
- `set_target_fps(fps: int)` - Set target framerate (30-240)
- `set_shader(shader_name: str)` - Set visualization shader
- `get_available_shaders() -> List[str]` - Get list of available shaders
- `get_audio_levels() -> Tuple[float, float, float]` - Get current audio levels (bass, mid, treble)
- `get_current_fps() -> float` - Get current rendering FPS

## OpenGL Compatibility

The component automatically handles OpenGL compatibility issues:

1. **Tests OpenGL support** before creating widgets
2. **Graceful fallback** to QWidget if QOpenGLWidget fails
3. **Wayland detection** and appropriate configuration
4. **Environment setup** for proper GLX/EGL integration

## Integration in UI Files

To use in Qt Designer `.ui` files:

1. Add a `QWidget` to your layout
2. Promote it to `VoiceVisualizerComponent`
3. Set the header to: `airunner.components.voice_visualizer.gui.widgets.voice_visualizer_component`

## Troubleshooting

If the visualizer fails to initialize:

1. Check that `libvoicevisualizer_widget.so` is present
2. Verify OpenGL drivers are installed
3. For Wayland users: XWayland compatibility is handled automatically
4. Check console output for detailed error messages

## Dependencies

- PySide6 with Qt 6.9+
- OpenGL 3.3+ support (recommended)
- Linux with PulseAudio for audio capture
- libvoicevisualizer_widget.so (included)
