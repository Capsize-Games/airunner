# Window Settings

This module provides the `WindowSettings` dataclass for storing and restoring the main window's geometry and state in AI Runner.

## Purpose
- Centralizes the definition of window state (size, position, maximized/fullscreen, and active tab).
- Used by the main window and settings mixin to persist and restore UI state.

## Components
- `WindowSettings`: Dataclass with fields for maximized/fullscreen state, window size, position, and active tab index.

## Usage
Import and use `WindowSettings` wherever you need to store or restore the main window's state:

```python
from airunner.components.settings.data.window_settings import WindowSettings

settings = WindowSettings(width=1024, height=768)
```

This ensures type consistency and avoids redefinition across modules.
