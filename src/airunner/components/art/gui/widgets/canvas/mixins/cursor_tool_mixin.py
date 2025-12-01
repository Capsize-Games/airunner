"""Mixin for cursor and tool management in CustomGraphicsView.

This mixin handles cursor caching, tool selection, and drag mode management.
"""

from typing import Optional, Dict, Tuple
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QGraphicsView

from airunner.enums import CanvasToolName
from airunner.gui.cursors.circle_brush import circle_cursor


class CursorToolMixin:
    """Provides cursor caching and tool management for graphics view.

    This mixin manages:
    - Cursor caching for performance
    - Current tool tracking
    - Drag mode toggling
    - Tool change signal handling

    Attributes:
        _cursor_cache: Dict mapping (tool, size) tuples to cursor objects
        _current_cursor: Currently active cursor
    """

    def __init__(self):
        """Initialize cursor and tool attributes."""
        super().__init__()
        self._cursor_cache: Dict[Tuple, object] = {}
        self._current_cursor: Optional[object] = None

    @property
    def current_tool(self) -> Optional[CanvasToolName]:
        """Get the currently active canvas tool.

        Returns:
            Current tool enum value, or None if no tool selected.
        """
        val = getattr(self.application_settings, "current_tool", None)
        try:
            return CanvasToolName(val) if val is not None else None
        except Exception:
            return None

    def get_cached_cursor(
        self, tool: CanvasToolName, size: int
    ) -> Optional[object]:
        """Get or create a cached cursor for the given tool and size.

        Caches cursors to avoid recreating them on every call, improving performance.

        Args:
            tool: The canvas tool type.
            size: Cursor size in pixels.

        Returns:
            Cached cursor object, or None if tool doesn't use custom cursor.
        """
        key = (tool, size)
        if key not in self._cursor_cache:
            if tool in (CanvasToolName.BRUSH, CanvasToolName.ERASER):
                # Create circle cursor for brush and eraser tools
                cursor = circle_cursor(
                    Qt.GlobalColor.white,
                    Qt.GlobalColor.transparent,
                    size,
                )
                self._cursor_cache[key] = cursor
        return self._cursor_cache.get(key)

    def toggle_drag_mode(self) -> None:
        """Set the view's drag mode.

        Currently always sets to NoDrag to prevent QGraphicsView's default
        drag behavior from interfering with custom pan implementation.
        """
        self.setDragMode(QGraphicsView.DragMode.NoDrag)

    def on_tool_changed_signal(self, message: dict) -> None:
        """Handle tool change signal.

        Updates drag mode, text item interaction, and active grid mouse acceptance
        when the active tool changes.

        Args:
            message: Signal message dict (unused but required by signal protocol).
        """
        self.toggle_drag_mode()
        # Update text item interaction flags based on tool
        # Ensure active grid area doesn't block item interaction while moving
        try:
            self._update_active_grid_mouse_acceptance()
        except Exception:
            pass
