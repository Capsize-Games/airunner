from typing import List, Optional, Dict, Tuple

from PySide6.QtCore import (
    QPointF,
    QPoint,
    Qt,
    QEvent,
    QSize,
    QTimer,
    QRectF,
)
from PySide6.QtWidgets import QGraphicsPixmapItem
from PySide6.QtGui import QMouseEvent, QColor, QBrush, QFont, QPen
from PySide6.QtWidgets import (
    QApplication,
    QGraphicsView,
    QGraphicsItemGroup,
    QGraphicsTextItem,
    QGraphicsRectItem,
    QMenu,
)
import json

from airunner.components.art.data.canvas_layer import CanvasLayer
from airunner.components.art.data.drawingpad_settings import DrawingPadSettings
from airunner.components.application.gui.windows.main.settings_mixin_shared_instance import (
    SettingsMixinSharedInstance,
)
from airunner.components.art.gui.widgets.canvas.draggables.draggable_text_item import (
    DraggableTextItem,
)
from airunner.components.art.gui.widgets.canvas.draggables.layer_image_item import (
    LayerImageItem,
)
from airunner.components.art.gui.widgets.canvas.resizable_text_item import (
    ResizableTextItem,
)
from airunner.enums import CanvasToolName, SignalCode, CanvasType
from airunner.components.art.gui.widgets.canvas.grid_graphics_item import (
    GridGraphicsItem,
)
from airunner.utils.application.mediator_mixin import MediatorMixin
from airunner.utils.image import convert_image_to_binary
from airunner.components.art.gui.widgets.canvas.brush_scene import BrushScene
from airunner.components.art.gui.widgets.canvas.custom_scene import CustomScene
from airunner.components.art.gui.widgets.canvas.draggables.active_grid_area import (
    ActiveGridArea,
)
from airunner.components.application.gui.windows.main.settings_mixin import (
    SettingsMixin,
)
from airunner.components.art.gui.widgets.canvas.zoom_handler import ZoomHandler
from airunner.gui.cursors.circle_brush import circle_cursor
from airunner.utils.settings import get_qsettings
from airunner.components.art.utils.canvas_position_manager import (
    CanvasPositionManager,
    ViewState,
)
from airunner.components.art.gui.widgets.canvas.text_inspector import (
    TextInspector,
)
from airunner.components.art.gui.widgets.canvas.mixins.cursor_tool_mixin import (
    CursorToolMixin,
)
from airunner.components.art.gui.widgets.canvas.mixins.scene_management_mixin import (
    SceneManagementMixin,
)
from airunner.components.art.gui.widgets.canvas.mixins.grid_drawing_mixin import (
    GridDrawingMixin,
)
from airunner.components.art.gui.widgets.canvas.mixins.viewport_positioning_mixin import (
    ViewportPositioningMixin,
)
from airunner.components.art.gui.widgets.canvas.mixins.event_handler_mixin import (
    EventHandlerMixin,
)
from airunner.components.art.gui.widgets.canvas.mixins.text_handling_mixin import (
    TextHandlingMixin,
)


class CustomGraphicsView(
    CursorToolMixin,
    SceneManagementMixin,
    GridDrawingMixin,
    ViewportPositioningMixin,
    EventHandlerMixin,
    TextHandlingMixin,
    MediatorMixin,
    SettingsMixin,
    QGraphicsView,
):
    """Custom graphics view for AI Runner canvas with pan, zoom, and drawing capabilities.

    This view manages canvas rendering, user interactions (mouse/keyboard events),
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
        # state for text-area drag/creation
        self._text_dragging = False
        self._text_drag_start = None
        self._temp_rubberband = None
        self.setMouseTracking(True)
        self._initialized = False
        self._scene: Optional[CustomScene] = None
        self._canvas_color: str = "#000000"
        self.current_background_color: Optional[QColor] = None
        self.active_grid_area: Optional[ActiveGridArea] = None
        self.do_draw_layers: bool = True
        self.initialized: bool = False
        self.drawing: bool = False
        self.pixmaps: Dict = {}
        self.line_group: Optional[QGraphicsItemGroup] = None
        self._scene_is_active: bool = False
        self.last_pos: QPoint = self.zero_point
        self.zoom_handler: ZoomHandler = ZoomHandler()
        self._canvas_offset = QPointF(0, 0)
        self._grid_compensation_offset = QPointF(
            0, 0
        )  # Tracks viewport compensation for grid alignment
        self.settings = get_qsettings()
        self._middle_mouse_pressed: bool = False
        self.grid_item = None
        self._text_items = []  # Store references to QGraphicsTextItem
        self._editing_text_item = None
        self._is_restoring_state = (
            False  # Flag to disable resize compensation during restoration
        )
        self.center_pos: QPointF = QPointF(0, 0)

        # Add settings to handle negative coordinates properly
        self.setAlignment(
            Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft
        )  # Set once here
        self._last_viewport_size = self.viewport().size()  # Track last size
        # Use SmartViewportUpdate to ensure proper repaints when items mutate in place
        self.setViewportUpdateMode(
            QGraphicsView.ViewportUpdateMode.SmartViewportUpdate
        )

        # Use setOptimizationFlags directly instead of the enum that doesn't exist in your PySide6 version
        self.setOptimizationFlags(
            QGraphicsView.OptimizationFlag.DontAdjustForAntialiasing
            | QGraphicsView.OptimizationFlag.DontSavePainterState
        )
        self.setFrameShape(QGraphicsView.Shape.NoFrame)

        # register signal handlers
        signal_handlers = {
            SignalCode.APPLICATION_TOOL_CHANGED_SIGNAL: self.on_tool_changed_signal,
            SignalCode.CANVAS_ZOOM_LEVEL_CHANGED: self.on_zoom_level_changed_signal,
            SignalCode.SET_CANVAS_COLOR_SIGNAL: self.set_canvas_color,
            SignalCode.UPDATE_SCENE_SIGNAL: self.update_scene,
            SignalCode.CANVAS_CLEAR_LINES_SIGNAL: self.clear_lines,
            SignalCode.SCENE_DO_DRAW_SIGNAL: self.on_canvas_do_draw_signal,
            SignalCode.APPLICATION_MAIN_WINDOW_LOADED_SIGNAL: self.on_main_window_loaded_signal,
            SignalCode.APPLICATION_SETTINGS_CHANGED_SIGNAL: self.on_application_settings_changed_signal,
            SignalCode.MASK_GENERATOR_WORKER_RESPONSE_SIGNAL: self.on_mask_generator_worker_response_signal,
            SignalCode.RECENTER_GRID_SIGNAL: self.on_recenter_grid_signal,
            SignalCode.CANVAS_IMAGE_UPDATED_SIGNAL: self.on_canvas_image_updated_signal,
            SignalCode.CANVAS_UPDATE_IMAGE_POSITIONS: self.updateImagePositions,
        }
        for k, v in signal_handlers.items():
            self.register(k, v)

        self._pan_update_timer = QTimer()
        self._pan_update_timer.setSingleShot(True)
        self._pan_update_timer.timeout.connect(self._do_pan_update)
        self._pending_pan_event = False

        self._cursor_cache = {}
        self._current_cursor = None

        # text inspector UI
        try:
            self._text_inspector = TextInspector(self)
            self._text_inspector.setVisible(False)
        except Exception:
            self._text_inspector = None

        # mapping of text item -> layer id
        self._text_item_layer_map = {}

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
        # Handle None values from mocked settings
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

        # DO NOT call update methods here - let the caller decide when to update
        # This prevents the offset from being modified during load

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
    def __do_show_active_grid_area(self) -> bool:
        """Check if active grid area should be shown for this canvas type.

        Returns:
            True if canvas type supports active grid area display.
        """
        return self.canvas_type in (
            CanvasType.IMAGE.value,
            CanvasType.BRUSH.value,
        )

    @property
    def layers(self) -> List[CanvasLayer]:
        return CanvasLayer.objects.filter_by(visible=True, locked=False)

    @property
    def viewport_center(self) -> QPointF:
        """Calculate the center point of the current viewport.

        Returns:
            Center point of viewport as QPointF.
        """
        viewport_size = self.viewport().size()
        return QPointF(viewport_size.width() / 2, viewport_size.height() / 2)

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

        # snapped_gx, snapped_gy = snap_to_grid(
        #     self.grid_settings,
        #     target_x,
        #     target_y,
        #     use_floor=False,
        # )

        # return int(round(snapped_gx)), int(round(snapped_gy))
        return target_x, target_y

    def original_item_positions(self) -> Dict[str, QPointF]:
        """Get the absolute positions of all layer items from the database.

        This method reads saved positions - it does NOT recalculate or modify them.
        Use recenter_layers() if you want to explicitly reposition layers.
        """
        layers = CanvasLayer.objects.order_by("order").all()
        original_item_positions = {}
        for index, layer in enumerate(layers):
            results = DrawingPadSettings.objects.filter_by(layer_id=layer.id)
            if len(results) == 0:
                continue

            drawingpad_settings = results[0]
            scene_item = self.scene._layer_items.get(layer.id)
            if scene_item is None:
                # Layer may not have been materialized yet; skip safely
                continue

            # Read the saved absolute position from the database
            # Do NOT recalculate - preserve what was saved
            if (
                drawingpad_settings.x_pos is not None
                and drawingpad_settings.y_pos is not None
            ):
                pos_x = drawingpad_settings.x_pos
                pos_y = drawingpad_settings.y_pos
            else:
                # If no saved position exists, use center of viewport as fallback
                item_rect = scene_item.boundingRect()
                image_width = item_rect.width()
                image_height = item_rect.height()
                pos_x, pos_y = self.get_recentered_position(
                    int(image_width), int(image_height)
                )
                # Save this calculated position for future use
                DrawingPadSettings.objects.update(
                    drawingpad_settings.id,
                    x_pos=pos_x,
                    y_pos=pos_y,
                )

            original_item_positions[scene_item] = QPointF(pos_x, pos_y)
        return original_item_positions

    def recenter_layer_positions(self) -> Dict[str, QPointF]:
        """Recalculate and save new centered positions for all layers.

        This is used when explicitly recentering (e.g., clicking recenter button).
        It calculates new absolute positions centered in the viewport and saves them.
        """
        layers = CanvasLayer.objects.order_by("order").all()
        self.logger.info(f"[RECENTER] Found {len(layers)} layers in database")
        new_positions = {}
        for layer in layers:
            self.logger.info(f"[RECENTER] Processing layer {layer.id}")
            results = DrawingPadSettings.objects.filter_by(layer_id=layer.id)
            self.logger.info(
                f"[RECENTER] Layer {layer.id}: found {len(results)} DrawingPadSettings"
            )
            if len(results) == 0:
                self.logger.warning(
                    f"[RECENTER] No DrawingPadSettings for layer {layer.id}"
                )
                continue

            drawingpad_settings = results[0]
            if not self.scene:
                self.logger.warning(f"[RECENTER] No scene!")
                continue

            self.logger.info(
                f"[RECENTER] Layer {layer.id}: _layer_items has {len(self.scene._layer_items)} items"
            )
            scene_item = self.scene._layer_items.get(layer.id)
            if scene_item is None:
                self.logger.warning(
                    f"[RECENTER] No scene_item for layer {layer.id} in _layer_items: {list(self.scene._layer_items.keys())}"
                )
                continue

            # Calculate new centered position
            item_rect = scene_item.boundingRect()
            image_width = item_rect.width()
            image_height = item_rect.height()
            pos_x, pos_y = self.get_recentered_position(
                int(image_width), int(image_height)
            )

            # Save the new position to database
            DrawingPadSettings.objects.update(
                drawingpad_settings.id,
                x_pos=pos_x,
                y_pos=pos_y,
            )

            new_positions[scene_item] = QPointF(pos_x, pos_y)
            self.logger.info(
                f"[RECENTER] Layer {layer.id}: saved to DB and dict - position x={pos_x}, y={pos_y}, scene_item id={id(scene_item)}"
            )

        self.logger.info(
            f"[RECENTER] Returning {len(new_positions)} positions"
        )
        return new_positions

    def align_canvas_items_to_viewport(self):
        # Don't recalculate center_pos if it was loaded from settings
        # (this preserves the grid origin across app restarts)
        # Only calculate if center_pos is still at the default (0,0)
        if self.center_pos == QPointF(0, 0):
            pos_x, pos_y = self.get_recentered_position(
                self.application_settings.working_width,
                self.application_settings.working_height,
            )
            self.center_pos = QPointF(pos_x, pos_y)
            self.logger.info(
                f"[ALIGN] Center pos calculated: x={pos_x}, y={pos_y}"
            )
        else:
            # Use existing center_pos from loaded settings
            pos_x = int(self.center_pos.x())
            pos_y = int(self.center_pos.y())
            self.logger.info(
                f"[ALIGN] Using loaded center pos: x={pos_x}, y={pos_y}"
            )

        self.update_active_grid_settings(
            pos_x=pos_x,
            pos_y=pos_y,
        )
        # Update display positions
        self.update_active_grid_area_position()

        self.updateImagePositions(self.original_item_positions())

    def on_recenter_grid_signal(self):
        self.canvas_offset = QPointF(0, 0)
        self._grid_compensation_offset = QPointF(
            0, 0
        )  # Reset grid compensation when recentering

        """Center the grid and all layer images in the viewport."""
        if not self.scene:
            return

        # Update active grid area absolute position in settings
        pos_x, pos_y = self.get_recentered_position(
            self.application_settings.working_width,
            self.application_settings.working_height,
        )
        self.center_pos = QPointF(pos_x, pos_y)
        self.update_active_grid_settings(
            pos_x=pos_x,
            pos_y=pos_y,
        )

        self.save_canvas_offset()

        self.api.art.canvas.update_grid_info(
            {
                "offset_x": self.canvas_offset_x,
                "offset_y": self.canvas_offset_y,
            }
        )

        # Update display positions
        self.update_active_grid_area_position()

        # Recalculate and save new centered positions
        # Handle BOTH old single-item system and new layer system
        new_positions = {}

        # OLD SYSTEM: Recenter the single DrawingPad item if it exists
        if self.scene.item:
            self.logger.info(
                "[RECENTER] Processing old single-item system (DrawingPad)"
            )
            item_rect = self.scene.item.boundingRect()
            image_width = item_rect.width()
            image_height = item_rect.height()
            pos_x, pos_y = self.get_recentered_position(
                int(image_width), int(image_height)
            )

            # Save to database
            self.update_drawing_pad_settings(x_pos=pos_x, y_pos=pos_y)

            # Add to positions dict
            new_positions[self.scene.item] = QPointF(pos_x, pos_y)
            self.logger.info(
                f"[RECENTER] DrawingPad item: saved to DB and dict - position x={pos_x}, y={pos_y}"
            )

        # NEW SYSTEM: Recenter layer items
        layer_positions = self.recenter_layer_positions()
        new_positions.update(layer_positions)

        self.logger.info(
            f"[RECENTER] Total items to recenter: {len(new_positions)}"
        )

        # CRITICAL: Clear caches AFTER saving to DB but BEFORE updating scene
        # This ensures scene.update_image_position() uses fresh DB values if
        # it needs to fall back to _get_layer_specific_settings()

        # Clear the scene's position cache
        if hasattr(self.scene, "original_item_positions"):
            self.scene.original_item_positions.clear()

        # Clear layer-specific settings cache
        shared_instance = SettingsMixinSharedInstance()
        keys_to_clear = [
            key
            for key in shared_instance._settings_cache_by_key.keys()
            if key.startswith(f"{DrawingPadSettings.__name__}_layer_")
        ]
        for key in keys_to_clear:
            shared_instance._settings_cache_by_key.pop(key, None)

        # Now update scene with the new positions
        self.updateImagePositions(new_positions)

        # Force complete redraw
        self.do_draw(force_draw=True)

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

    def show_active_grid_area(self):
        if not self.__do_show_active_grid_area:
            # Ensure it's removed if disabled
            if self.active_grid_area:
                self.remove_scene_item(self.active_grid_area)
                self.active_grid_area = None
            return

        # Skip repositioning during drag to prevent interference
        if self.scene and getattr(self.scene, "is_dragging", False):
            self.logger.info(
                "[ACTIVE GRID] Skipping show_active_grid_area - is_dragging is True"
            )
            return

        # Create if it doesn't exist
        if not self.active_grid_area:
            self.active_grid_area = ActiveGridArea()
            self.active_grid_area.setZValue(10000)
            self.scene.addItem(self.active_grid_area)
            # Connect the signal emitted by the updated update_position
            self.active_grid_area.register(
                SignalCode.APPLICATION_ACTIVE_GRID_AREA_UPDATED,
                self.update_active_grid_area_position,  # Call view's update method
            )

        # Get the stored absolute position (defaults to 0,0 if not found)
        # Use active_grid_settings as the primary source, QSettings as fallback/persistence
        absolute_x = self.active_grid_settings.pos_x
        absolute_y = self.active_grid_settings.pos_y

        self.logger.info(
            f"[LOAD GRID] Active grid absolute position from DB: x={absolute_x}, y={absolute_y}, canvas_offset=({self.canvas_offset_x}, {self.canvas_offset_y})"
        )

        # If settings are somehow None (e.g., first run), default and save
        if absolute_x is None or absolute_y is None:
            # Default to centering in the initial view, considering the initial offset
            viewport_center_x = self.viewport().width() / 2
            viewport_center_y = self.viewport().height() / 2
            # Calculate absolute position needed to appear centered with current offset
            absolute_x = (
                viewport_center_x
                + self.canvas_offset_x
                - (self.application_settings.working_width / 2)
            )
            absolute_y = (
                viewport_center_y
                + self.canvas_offset_y
                - (self.application_settings.working_height / 2)
            )

            # Save this initial absolute position
            self.update_active_grid_settings(
                pos_x=int(round(absolute_x)), pos_y=int(round(absolute_y))
            )
            self.settings.sync()

        # Calculate and set the display position using CanvasPositionManager
        # to account for both canvas_offset and grid_compensation
        manager = CanvasPositionManager()
        view_state = ViewState(
            canvas_offset=self.canvas_offset,
            grid_compensation=self._grid_compensation_offset,
        )
        absolute_pos = QPointF(absolute_x, absolute_y)
        display_pos = manager.absolute_to_display(absolute_pos, view_state)

        self.logger.info(
            f"[LOAD GRID] Setting grid display position: x={display_pos.x()}, y={display_pos.y()} (absolute: {absolute_x}, {absolute_y}, offset: {self.canvas_offset_x}, {self.canvas_offset_y}, compensation: {self._grid_compensation_offset.x()}, {self._grid_compensation_offset.y()})"
        )
        self.active_grid_area.setPos(display_pos.x(), display_pos.y())

        # Log actual scene position after setPos
        actual_pos = self.active_grid_area.scenePos()
        self.logger.info(
            f"[LOAD GRID] Active grid actual scene position after setPos: ({actual_pos.x()}, {actual_pos.y()})"
        )

        # Ensure active grid mouse acceptance matches current tool
        try:
            self._update_active_grid_mouse_acceptance()
        except Exception:
            pass

    def _update_active_grid_mouse_acceptance(self):
        """Make the active grid area ignore mouse events while the MOVE tool is active.

        When the MOVE tool is selected users need to be able to interact with items
        beneath the active grid area. Setting accepted mouse buttons to NoButton
        makes the item transparent to mouse events so clicks fall through.
        """
        if not self.active_grid_area:
            return

        try:
            # If MOVE tool is active, let clicks pass through the active grid area
            if self.current_tool is CanvasToolName.MOVE:
                self.active_grid_area.setAcceptedMouseButtons(
                    Qt.MouseButton.NoButton
                )
                # Also disable hover events so hover cursors don't block underlying items
                try:
                    self.active_grid_area.setAcceptHoverEvents(False)
                except Exception:
                    pass
            else:
                # Restore acceptance for left/right buttons when not moving
                accepted = (
                    Qt.MouseButton.LeftButton | Qt.MouseButton.RightButton
                )
                self.active_grid_area.setAcceptedMouseButtons(accepted)
                try:
                    self.active_grid_area.setAcceptHoverEvents(True)
                except Exception:
                    pass
        except Exception:
            # Best-effort; do not break flow if ActiveGridArea doesn't support these methods
            self.logger.exception(
                "Failed updating active grid mouse acceptance"
            )

    def on_zoom_level_changed_signal(self):
        transform = self.zoom_handler.on_zoom_level_changed()

        # Set the transform
        self.setTransform(transform)

        # Redraw lines
        self.do_draw()

    def wheelEvent(self, event):
        # Only allow zooming with Ctrl, otherwise ignore scrolling
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            super().wheelEvent(event)
            self.draw_grid()  # Only redraw grid on zoom
        else:
            event.ignore()  # Prevent QGraphicsView from scrolling

    def contextMenuEvent(self, event):
        """Show a delete context menu for images and text items under cursor."""
        try:
            scene_pos = self.mapToScene(event.pos())
        except Exception:
            return

        try:
            items = self.scene.items(scene_pos)
        except Exception:
            items = []

        if not items:
            return

        try:
            menu = QMenu()
            delete_action = menu.addAction(self.tr("Delete"))
            chosen = menu.exec_(event.globalPos())

            if chosen == delete_action:
                # Find first deletable item (skip grid and active grid area)
                deletable = None
                for cand in items:
                    if not isinstance(
                        cand, (GridGraphicsItem, ActiveGridArea)
                    ):
                        deletable = cand
                        break

                if deletable is None:
                    return

                target = deletable

                # Text item deletion
                if target in getattr(self, "_text_items", []):
                    self._remove_text_item(target)
                # Pixmap item deletion (images)
                elif isinstance(target, QGraphicsPixmapItem):
                    self._remove_layer_image_item(target)
                # Other items: just remove from scene
                else:
                    getattr(target, "layer_id", None)
                    self._remove_layer_image_item(target)
                    try:
                        if target.scene():
                            target.scene().removeItem(target)
                    except Exception:
                        pass
        except Exception:
            pass

    def _remove_layer_image_item(self, target):
        try:
            # If it's a LayerImageItem, clear the persisted layer image
            if isinstance(target, LayerImageItem):
                layer_id = getattr(target, "layer_id", None)
                try:
                    if target.scene():
                        target.scene().removeItem(target)
                except Exception:
                    pass

                # Remove from scene layer mapping
                try:
                    if self.scene and hasattr(self.scene, "_layer_items"):
                        for k, v in list(self.scene._layer_items.items()):
                            if v is target:
                                del self.scene._layer_items[k]
                                break
                except Exception:
                    pass

                # Clear persisted image for this layer
                try:
                    if layer_id is not None:
                        self.logger.info(
                            f"Clearing persisted image for layer {layer_id}"
                        )
                        self.update_drawing_pad_settings(
                            layer_id=layer_id, image=None
                        )

                        # Verify it was cleared
                        try:
                            settings = (
                                DrawingPadSettings.objects.filter_by_first(
                                    layer_id=layer_id
                                )
                            )
                            if settings:
                                has_image = settings.image is not None
                                self.logger.info(
                                    f"After clearing: layer {layer_id} still has image: {has_image}"
                                )
                            else:
                                self.logger.warning(
                                    f"No settings found for layer {layer_id} after update"
                                )
                        except Exception as e:
                            self.logger.exception(
                                f"Failed to verify image clear: {e}"
                            )

                        self.api.art.canvas.image_updated()
                except Exception as e:
                    self.logger.exception(
                        f"Failed to clear persisted image: {e}"
                    )
            # If it's the scene's primary item, use scene.delete_image()
            elif self.scene and getattr(self.scene, "item", None) is target:
                try:
                    self.scene.delete_image()
                except Exception:
                    try:
                        self.scene.current_active_image = None
                    except Exception:
                        pass
            # Generic pixmap: just remove it
            else:
                try:
                    if target.scene():
                        target.scene().removeItem(target)
                except Exception:
                    pass
        except Exception:
            try:
                if target.scene():
                    target.scene().removeItem(target)
            except Exception:
                pass

    def _do_pan_update(self):
        self.update_active_grid_area_position()
        self.updateImagePositions()
        self.draw_grid()
        if self._pending_pan_event:
            self._pending_pan_event = False
            self._pan_update_timer.start(1)

    def _finish_state_restoration(self):
        """Called after a delay to finish state restoration and re-enable resize compensation."""
        self._is_restoring_state = False

        # Reload and reapply the canvas offset one final time to ensure it's correct
        x = self.settings.value("canvas_offset_x", 0.0)
        y = self.settings.value("canvas_offset_y", 0.0)
        final_offset = QPointF(float(x), float(y))
        self.canvas_offset = final_offset

        # Update positions one final time
        self.update_active_grid_area_position()
        self.updateImagePositions()

        self.logger.debug(
            f"Canvas state restoration complete - final offset: ({final_offset.x()}, {final_offset.y()})"
        )
        self.scene.show_event()

    def _apply_viewport_compensation(self, shift_x: float, shift_y: float):
        """Apply viewport center compensation by adjusting the grid compensation offset.

        This method shifts only the grid compensation offset so items appear to stay
        centered relative to the viewport, without changing the canvas_offset value
        or the stored absolute positions in the database.

        The CanvasPositionManager will automatically apply the grid_compensation
        when converting absolute positions to display positions, so we don't need
        to modify the cached absolute positions.
        """
        if not self.scene:
            return

        # Skip if the shift is negligible
        if abs(shift_x) < 0.5 and abs(shift_y) < 0.5:
            return

        self.logger.info(
            f"[VIEWPORT COMPENSATION] Applying shift: ({shift_x}, {shift_y}), "
            f"old_compensation=({self._grid_compensation_offset.x()}, {self._grid_compensation_offset.y()}), "
            f"_is_restoring_state={self._is_restoring_state}, _initialized={self._initialized}"
        )

        # Adjust the grid compensation offset
        # This shifts the grid origin to maintain alignment with the viewport center
        self._grid_compensation_offset = QPointF(
            self._grid_compensation_offset.x() + shift_x,
            self._grid_compensation_offset.y() + shift_y,
        )

        self.logger.info(
            f"[VIEWPORT COMPENSATION] New compensation: ({self._grid_compensation_offset.x()}, {self._grid_compensation_offset.y()})"
        )

        # DO NOT modify the scene's original_item_positions here!
        # The CanvasPositionManager.absolute_to_display() already applies
        # grid_compensation in its calculation:
        # display_pos = absolute_pos - canvas_offset + grid_compensation
        #
        # If we shift the absolute positions here, we would be double-applying
        # the compensation, causing items to drift during window resize.

        # Update the visual positions using the new grid_compensation
        # The position manager will automatically apply it
        self.update_active_grid_area_position()
        self.updateImagePositions()

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
        # Update text item interaction flags based on tool
        is_text = self.current_tool is CanvasToolName.TEXT
        self._set_text_items_interaction(is_text)
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

        # Use the scene's update_image_position method which handles both
        # the old single-item system and the new layer system
        self.scene.update_image_position(
            self.canvas_offset, original_item_positions
        )

        # Force entire viewport update to handle negative coordinates
        self.viewport().update()
        # After images/positions update, restore any text items persisted to DB
        try:
            self._restore_text_items_from_db()
        except Exception:
            self.logger.exception(
                "Failed to restore text items after updateImagePositions"
            )

    def enterEvent(self, event: QEvent) -> None:
        """
        Handle the event when the mouse enters the CustomGraphicsView widget.
        Let the scene handle the cursor based on the current tool.
        """
        self.scene.enterEvent(event)
        super().enterEvent(event)
        # Remove the forced crosshair cursor to let the custom cursor logic work
        # self.setCursor(Qt.CursorShape.CrossCursor)  # This was forcing the plus sign cursor

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
        # Force complete layer refresh from database
        if hasattr(self.scene, "_refresh_layer_display"):
            self.scene._refresh_layer_display()

        self.do_draw(force_draw=True)

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
