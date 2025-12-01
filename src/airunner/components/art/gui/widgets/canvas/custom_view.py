from typing import Optional, Dict, Tuple

from PySide6.QtCore import (
    QPointF,
    QEvent,
    QSize,
)
from PySide6.QtGui import QColor, QBrush, QFont
from PySide6.QtWidgets import (
    QGraphicsView,
)

from airunner.enums import CanvasToolName, CanvasType
from airunner.components.art.gui.widgets.canvas.grid_graphics_item import (
    GridGraphicsItem,
)
from airunner.utils.application.mediator_mixin import MediatorMixin
from airunner.utils.image import convert_image_to_binary
from airunner.components.art.gui.widgets.canvas.brush_scene import BrushScene
from airunner.components.art.gui.widgets.canvas.custom_scene import CustomScene
from airunner.components.application.gui.windows.main.settings_mixin import (
    SettingsMixin,
)
from airunner.components.art.gui.widgets.canvas.mixins.view_mixins import (
    CursorToolMixin,
    SceneManagementMixin,
    GridDrawingMixin,
    ViewportPositioningMixin,
    EventHandlerMixin,
    LayerItemManagementMixin,
    ActiveGridAreaMixin,
    PanOffsetMixin,
    ZoomMixin,
    InitializationMixin,
    RecenteringMixin,
    ContextMenuMixin,
    PositionManagementMixin,
)


class CustomGraphicsView(
    InitializationMixin,
    RecenteringMixin,
    ContextMenuMixin,
    PositionManagementMixin,
    LayerItemManagementMixin,
    ActiveGridAreaMixin,
    PanOffsetMixin,
    ZoomMixin,
    CursorToolMixin,
    SceneManagementMixin,
    GridDrawingMixin,
    ViewportPositioningMixin,
    EventHandlerMixin,
    MediatorMixin,
    SettingsMixin,
    QGraphicsView,
):
    """Custom graphics view for AI Runner canvas with pan, zoom, and drawing capabilities.

        This view manages canvas rendering, user interactions (mouse/keyboard events),
    ```
        grid display, layer positioning, and text editing. It handles viewport transformations
        to maintain visual consistency during window resizes and user pan/zoom operations.

        Key Features:
        - Canvas offset management for panning
        - Grid and active grid area display
        - Layer image positioning with absolute/display coordinate conversion
        - Text item creation and editing with inspector UI
        - Zoom and viewport compensation
        - Context menu for item deletion
        - Cursor management based on current tool

        Attributes:
            canvas_offset: User's pan position (QPointF)
            grid_compensation_offset: Viewport compensation for grid alignment
            center_pos: Grid origin position
            active_grid_area: Visual representation of working area
            grid_item: Grid lines graphics item
            zoom_handler: Manages zoom transformations
            _text_items: List of text items on canvas
            _text_inspector: UI for text formatting
    """

    def __init__(self, *args, **kwargs):
        super().__init__()
        self._initialize_attributes()
        self._configure_view_settings()
        self._register_signal_handlers()
        self._setup_pan_timer()

    @property
    def canvas_offset(self) -> QPointF:
        """Get the current canvas pan offset.

        Returns:
            Current canvas offset as QPointF.
        """
        return self._canvas_offset

    @canvas_offset.setter
    def canvas_offset(self, value: QPointF) -> None:
        """Set the canvas pan offset.

        Args:
            value: New canvas offset as QPointF.
        """
        self._canvas_offset = value

    @property
    def canvas_offset_x(self) -> float:
        """Get the X component of canvas offset.

        Returns:
            X offset in pixels.
        """
        return self.canvas_offset.x()

    @property
    def canvas_offset_y(self) -> float:
        """Get the Y component of canvas offset.

        Returns:
            Y offset in pixels.
        """
        return self.canvas_offset.y()

    @property
    def zero_point(self) -> QPointF:
        """Get a zero point QPointF(0, 0).

        Returns:
            QPointF at origin.
        """
        return QPointF(0, 0)  # Return QPointF instead of QPoint

    @property
    def grid_compensation_offset(self) -> QPointF:
        """Accumulated viewport compensation offset for grid alignment."""
        return self._grid_compensation_offset

    def load_canvas_offset(self):
        """Load the canvas offset from QSettings."""
        x = self.settings.value("canvas_offset_x", 0.0)  # Default to 0
        y = self.settings.value("canvas_offset_y", 0.0)  # Default to 0
        x = float(x) if x is not None else 0.0
        y = float(y) if y is not None else 0.0
        loaded_offset = QPointF(x, y)
        self.canvas_offset = loaded_offset

        self.logger.info(
            f"[LOAD] Canvas offset loaded from settings: x={x}, y={y}"
        )

        # Load center_pos (grid origin)
        center_x = self.settings.value("center_pos_x", None)
        center_y = self.settings.value("center_pos_y", None)
        if center_x is not None and center_y is not None:
            self.center_pos = QPointF(float(center_x), float(center_y))
            self.logger.info(
                f"[LOAD] Center pos loaded from settings: x={center_x}, y={center_y}"
            )
        else:
            # Will be calculated on first recenter or in showEvent
            self.center_pos = QPointF(0, 0)

    def save_canvas_offset(self):
        """Save the canvas offset to QSettings."""
        self.settings.setValue("canvas_offset_x", self.canvas_offset_x)
        self.settings.setValue("canvas_offset_y", self.canvas_offset_y)
        self.logger.info(
            f"[SAVE] Canvas offset saved: x={self.canvas_offset_x}, y={self.canvas_offset_y}"
        )

        # Save center_pos (grid origin)
        self.settings.setValue("center_pos_x", self.center_pos.x())
        self.settings.setValue("center_pos_y", self.center_pos.y())
        self.logger.info(
            f"[SAVE] Center pos saved: x={self.center_pos.x()}, y={self.center_pos.y()}"
        )
        
        # Ensure settings are written to disk immediately
        self.settings.sync()

    @property
    def scene(self) -> Optional[CustomScene]:
        """Get or create the graphics scene for this view.

        Creates appropriate scene type (CustomScene for image canvas,
        BrushScene for brush canvas) based on canvas_type property.

        Returns:
            The graphics scene instance, or None if canvas_type is invalid.
        """
        scene = self._scene
        if not scene and self.canvas_type:
            if self.canvas_type == CanvasType.IMAGE.value:
                scene = CustomScene(canvas_type=self.canvas_type)
            elif self.canvas_type == CanvasType.BRUSH.value:
                scene = BrushScene(canvas_type=self.canvas_type)
            else:
                self.logger.error(f"Unknown canvas type: {self.canvas_type}")
                return

        if scene:
            scene.parent = self
            self._scene = scene
            self.setScene(scene)
            self.set_canvas_color(scene)
        return self._scene

    @scene.setter
    def scene(self, value: Optional[CustomScene]) -> None:
        """Set the graphics scene.

        Args:
            value: The scene instance to set.
        """
        self._scene = value

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

    @property
    def canvas_type(self) -> str:
        """Get the canvas type (image/brush).

        Returns:
            Canvas type string from Qt property.
        """
        return self.property("canvas_type")

    @property
    def _do_show_active_grid_area(self) -> bool:
        """Check if active grid area should be shown for this canvas type.

        Returns:
            True if canvas type supports active grid area display.
        """
        return self.canvas_type in (
            CanvasType.IMAGE.value,
            CanvasType.BRUSH.value,
        )

    def get_recentered_position(
        self, width: float, height: float
    ) -> Tuple[float, float]:
        """Calculate position to center an item of given size in the viewport.

        Args:
            width: Width of item to center.
            height: Height of item to center.

        Returns:
            Tuple of (x, y) coordinates for top-left corner to center the item.
        """
        viewport_center_x = self.viewport_center.x()
        viewport_center_y = self.viewport_center.y()

        item_center_x = width / 2.0
        item_center_y = height / 2.0

        target_x = viewport_center_x - item_center_x
        target_y = viewport_center_y - item_center_y
        return target_x, target_y

    def on_mask_generator_worker_response_signal(self, message: dict):
        mask = message["mask"]
        if mask is not None:
            mask = convert_image_to_binary(mask)
            self.update_drawing_pad_settings(mask=mask)

    def on_main_window_loaded_signal(self):
        self.initialized = True
        self.do_draw()

    def on_canvas_do_draw_signal(self, data: dict):
        self.do_draw(force_draw=data.get("force_draw", False))

    def on_application_settings_changed_signal(self, data: Dict):
        if data.get("setting_name") == "grid_settings":
            if (
                data.get("column_name") == "canvas_color"
                and self._canvas_color != data.get("value", self._canvas_color)
                and self.scene
            ):
                self._canvas_color = data.get("value")
                self.set_canvas_color(self.scene, self._canvas_color)

            if self.grid_settings.show_grid:
                self.do_draw(force_draw=True)
            else:
                self.clear_lines()

    def do_draw(self, force_draw: bool = False, size: Optional[QSize] = None):
        if self.scene is None:
            return
        if (self.drawing or not self.initialized) and not force_draw:
            return
        self.drawing = True
        self.set_scene_rect()

        # Remove old grid item if it exists
        if self.grid_item is not None:
            self.scene.removeItem(self.grid_item)
            self.grid_item = None

        # Add a single efficient grid item
        if self.grid_settings.show_grid:
            self.grid_item = GridGraphicsItem(self, self.center_pos)
            self.scene.addItem(self.grid_item)

        self.show_active_grid_area()
        self.update_scene()
        self.drawing = False

    def draw_grid(self, size: Optional[QSize] = None):
        if self.grid_item:
            self.grid_item.update()

    def clear_lines(self):
        if self.grid_item is not None:
            self.scene.removeItem(self.grid_item)
            self.grid_item = None

    def set_scene_rect(self):
        if not self.scene:
            return
        canvas_container_size = self.viewport().size()
        self.scene.setSceneRect(
            0, 0, canvas_container_size.width(), canvas_container_size.height()
        )

    def update_scene(self):
        if not self.scene:
            return
        self.scene.update()

    def remove_scene_item(self, item):
        if item is None:
            return
        if item.scene() == self.scene:
            self.scene.removeItem(item)

    def set_canvas_color(
        self,
        scene: Optional[CustomScene] = None,
        canvas_color: Optional[str] = None,
    ):
        scene = self.scene if not scene else scene
        canvas_color = canvas_color or self.grid_settings.canvas_color
        self.current_background_color = canvas_color
        color = QColor(self.current_background_color)
        brush = QBrush(color)
        scene.setBackgroundBrush(brush)

    def on_tool_changed_signal(self, message):
        self.toggle_drag_mode()
        # Ensure active grid area doesn't block item interaction while moving
        try:
            self._update_active_grid_mouse_acceptance()
        except Exception:
            pass

    def updateImagePositions(
        self, original_item_positions: Dict[str, QPointF] = None
    ):
        """Update positions of all images in the scene based on canvas offset."""
        if not self.scene:
            self.logger.error("No scene in updateImagePositions")
            return

        self.scene.update_image_position(
            self.canvas_offset, original_item_positions
        )

        # Force entire viewport update to handle negative coordinates
        self.viewport().update()

    def enterEvent(self, event: QEvent) -> None:
        """
        Handle the event when the mouse enters the CustomGraphicsView widget.
        Let the scene handle the cursor based on the current tool.
        """
        self.scene.enterEvent(event)
        super().enterEvent(event)

    def leaveEvent(self, event: QEvent) -> None:
        """
        Handle the event when the mouse leaves the CustomGraphicsView widget.
        Resets the cursor to a normal pointer.
        """
        self.scene.leaveEvent(event)
        super().leaveEvent(event)

    def on_canvas_image_updated_signal(self, *args):
        """Handler for when images are updated or added to the canvas.
        Ensures that newly generated images respect the current pan position.
        """
        # Layer refresh is already scheduled in canvas_generation_mixin
        # Skip redundant refresh to avoid blocking the UI thread
        # if hasattr(self.scene, "_refresh_layer_display"):
        #     self.scene._refresh_layer_display()

        # Defer the redraw to avoid blocking
        from PySide6.QtCore import QTimer

        QTimer.singleShot(0, lambda: self.do_draw(force_draw=True))

    def _get_default_text_font(self):
        font = QFont()
        font.setPointSize(18)
        font.setFamily("Arial")
        return font

    def update_drawing_pad_settings(self, **kwargs):
        # Extract layer_id if provided in kwargs
        specific_layer_id = kwargs.pop("layer_id", None)

        if specific_layer_id is not None:
            # Update only the specific layer
            super().update_drawing_pad_settings(
                layer_id=specific_layer_id, **kwargs
            )
        else:
            # Update all layers if no specific layer_id provided
            for layer_item in self.layers:
                super().update_drawing_pad_settings(
                    layer_id=layer_item.id, **kwargs
                )
