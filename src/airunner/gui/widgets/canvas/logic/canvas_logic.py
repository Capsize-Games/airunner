from typing import Optional
from PySide6.QtCore import QPoint
from airunner.enums import CanvasToolName


class CanvasLogic:
    """Business logic for canvas state, tool selection, and settings."""

    def __init__(self, application_settings, update_application_settings):
        self.application_settings = application_settings
        self.update_application_settings = update_application_settings

    @property
    def current_tool(self) -> Optional[CanvasToolName]:
        val = self.application_settings.current_tool
        if val is None:
            return None
        try:
            return CanvasToolName(val)
        except Exception:
            return None

    @property
    def image_pivot_point(self) -> QPoint:
        settings = self.application_settings
        try:
            return QPoint(settings.pivot_point_x, settings.pivot_point_y)
        except Exception:
            return QPoint(0, 0)

    @image_pivot_point.setter
    def image_pivot_point(self, value: QPoint):
        settings = self.application_settings
        settings.pivot_point_x = value.x()
        settings.pivot_point_y = value.y()
        self.update_application_settings("pivot_point_x", value.x())
        self.update_application_settings("pivot_point_y", value.y())

    def update_action_buttons(self, ui, grid_settings, tool, active):
        """Update the checked/unchecked state of action buttons based on tool and grid state."""
        ui.active_grid_area_button.blockSignals(True)
        ui.brush_button.blockSignals(True)
        ui.eraser_button.blockSignals(True)
        ui.text_button.blockSignals(True)
        ui.grid_button.blockSignals(True)
        ui.active_grid_area_button.setChecked(
            tool is CanvasToolName.ACTIVE_GRID_AREA and active
        )
        ui.brush_button.setChecked(tool is CanvasToolName.BRUSH and active)
        ui.eraser_button.setChecked(tool is CanvasToolName.ERASER and active)
        ui.text_button.setChecked(tool is CanvasToolName.TEXT and active)
        ui.grid_button.setChecked(grid_settings.show_grid)
        ui.active_grid_area_button.blockSignals(False)
        ui.brush_button.blockSignals(False)
        ui.eraser_button.blockSignals(False)
        ui.text_button.blockSignals(False)
        ui.grid_button.blockSignals(False)

    def set_tool(self, tool, active):
        """Set the current tool in application settings."""
        self.update_application_settings(
            "current_tool", tool.value if (tool and active) else None
        )

    def set_grid(self, grid_settings, val: bool):
        """Set the grid visibility in grid settings."""
        grid_settings.show_grid = val
        # Optionally, update persistent settings if needed

    def get_cursor_type(
        self, current_tool, event=None, brush_size=32, apply_cursor=True
    ) -> str:
        """Return a string describing the cursor type for the given tool and event."""
        if not apply_cursor:
            return "arrow"
        if (
            event
            and hasattr(event, "button")
            and event.button() == 2  # Qt.MouseButton.MiddleButton
        ):
            return "closed_hand"
        if current_tool in (CanvasToolName.BRUSH, CanvasToolName.ERASER):
            return "circle_brush"
        if current_tool is CanvasToolName.ACTIVE_GRID_AREA:
            if (
                event
                and hasattr(event, "buttons")
                and event.buttons() == 1  # Qt.MouseButton.LeftButton
            ):
                return "closed_hand"
            return "open_hand"
        if current_tool is CanvasToolName.NONE:
            return "arrow"
        return "arrow"
