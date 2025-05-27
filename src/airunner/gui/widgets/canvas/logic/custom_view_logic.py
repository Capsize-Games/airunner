"""
Business logic for CustomGraphicsView: tool/grid state, cursor, and text item logic.
Decoupled from PySide6 GUI code for testability.
"""

from typing import Optional
from PySide6.QtCore import Qt
from airunner.enums import CanvasToolName


class CustomViewLogic:
    def __init__(self, application_settings, update_application_settings):
        self.application_settings = application_settings
        self.update_application_settings = update_application_settings
        self._cursor_cache = {}
        self._current_cursor = None

    def get_current_tool(self) -> Optional[CanvasToolName]:
        val = getattr(self.application_settings, "current_tool", None)
        try:
            return CanvasToolName(val) if val is not None else None
        except Exception:
            return None

    def get_cursor(self, current_tool, event=None, brush_size=32, apply_cursor=True):
        from airunner.gui.cursors.circle_brush import circle_cursor

        if not apply_cursor:
            return Qt.CursorShape.ArrowCursor
        if (
            event
            and hasattr(event, "button")
            and event.button() == Qt.MouseButton.MiddleButton
        ):
            return Qt.CursorShape.ClosedHandCursor
        if current_tool in (CanvasToolName.BRUSH, CanvasToolName.ERASER):
            return circle_cursor(
                Qt.GlobalColor.white, Qt.GlobalColor.transparent, brush_size
            )
        if current_tool is CanvasToolName.TEXT:
            return Qt.CursorShape.IBeamCursor
        if current_tool is CanvasToolName.ACTIVE_GRID_AREA:
            if (
                event
                and hasattr(event, "buttons")
                and event.buttons() == Qt.MouseButton.LeftButton
            ):
                return Qt.CursorShape.ClosedHandCursor
            return Qt.CursorShape.OpenHandCursor
        if current_tool is CanvasToolName.NONE:
            return Qt.CursorShape.ArrowCursor
        return Qt.CursorShape.ArrowCursor

    def cache_cursor(self, tool, size, cursor):
        self._cursor_cache[(tool, size)] = cursor

    def get_cached_cursor(self, tool, size):
        return self._cursor_cache.get((tool, size))
