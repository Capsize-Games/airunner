"""Compatibility wrapper for legacy Qt resource imports.

The UI layer still imports ``airunner.feather_rc`` for compatibility, even
though the standard SVG asset set registered by the compiled resource module
is now sourced from Lucide. The generated file under
``airunner/gui/resources`` remains the canonical output produced by the UI
build step; this wrapper simply re-exports it so existing imports keep
working unchanged.
"""

from airunner.gui.resources.feather_rc import *  # noqa: F401,F403
