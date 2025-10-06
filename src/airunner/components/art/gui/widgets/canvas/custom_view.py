from typing import List, Optional, Dict, Tuple
import time

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
from PySide6.QtCore import QThread
import json

from airunner.components.art.data.canvas_layer import CanvasLayer
from airunner.components.art.data.drawingpad_settings import DrawingPadSettings
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
from airunner.utils.application.snap_to_grid import snap_to_grid
from airunner.components.art.gui.widgets.canvas.text_inspector import (
    TextInspector,
)


class DraggableTextItem(QGraphicsTextItem):
    """A text item that supports dragging in MOVE tool and reports position changes back to the view."""

    def __init__(self, view: "CustomGraphicsView"):
        super().__init__()
        self._view = view
        self.initial_mouse_scene_pos = None
        self.initial_item_abs_pos = None
        self.mouse_press_pos = None
        self._current_snapped_pos = (0, 0)

    @property
    def current_tool(self):
        try:
            return self._view.current_tool
        except Exception:
            return None

    def mousePressEvent(self, event):
        # Only initiate custom drag when in MOVE tool
        if self.current_tool not in [CanvasToolName.MOVE]:
            return QGraphicsTextItem.mousePressEvent(self, event)

        if event.button() == Qt.MouseButton.LeftButton:
            self.initial_mouse_scene_pos = event.scenePos()

            # Use the item's current scene position to compute initial absolute
            # coordinates for dragging. Previously this used persisted layer
            # settings which could be stale, causing the item to jump when the
            # user started dragging. Using scenePos() (plus canvas offset)
            # reflects the true displayed position and prevents the jump.
            try:
                item_scene_pos = self.scenePos()
                canvas_offset = self._view.canvas_offset
                abs_x = item_scene_pos.x() + canvas_offset.x()
                abs_y = item_scene_pos.y() + canvas_offset.y()
            except Exception:
                abs_x = int(self.x() + self._view.canvas_offset_x)
                abs_y = int(self.y() + self._view.canvas_offset_y)

            self.initial_item_abs_pos = QPointF(abs_x, abs_y)
            self.mouse_press_pos = event.pos()
            event.accept()
        else:
            # Show a simple context menu on right-click to delete the text
            if event.button() == Qt.MouseButton.RightButton:
                try:
                    menu = QMenu()
                    delete_action = menu.addAction(self.tr("Delete"))
                    chosen = menu.exec_(event.screenPos())
                    if chosen == delete_action:
                        view = getattr(self, "_view", None)
                        if view is not None:
                            view._remove_text_item(self)
                        return
                except Exception:
                    pass
                return
            return QGraphicsTextItem.mousePressEvent(self, event)

    def mouseMoveEvent(self, event):
        if self.current_tool not in [CanvasToolName.MOVE]:
            return QGraphicsTextItem.mouseMoveEvent(self, event)

        if self.initial_mouse_scene_pos is not None:
            delta = event.scenePos() - self.initial_mouse_scene_pos
            proposed_abs_x = self.initial_item_abs_pos.x() + delta.x()
            proposed_abs_y = self.initial_item_abs_pos.y() + delta.y()

            # Snap to grid if enabled
            if self._view.grid_settings.snap_to_grid:
                snapped_abs_x, snapped_abs_y = snap_to_grid(
                    self._view.grid_settings, proposed_abs_x, proposed_abs_y
                )
            else:
                snapped_abs_x, snapped_abs_y = proposed_abs_x, proposed_abs_y

            canvas_offset = self._view.canvas_offset
            display_x = snapped_abs_x - canvas_offset.x()
            display_y = snapped_abs_y - canvas_offset.y()
            self.setPos(display_x, display_y)
            self._current_snapped_pos = (
                int(snapped_abs_x),
                int(snapped_abs_y),
            )
            event.accept()
        else:
            return QGraphicsTextItem.mouseMoveEvent(self, event)

    def mouseReleaseEvent(self, event):
        if self.current_tool not in [CanvasToolName.MOVE]:
            return QGraphicsTextItem.mouseReleaseEvent(self, event)

        if self.initial_mouse_scene_pos is not None:
            has_moved = False
            if self.mouse_press_pos:
                has_moved = (
                    self.mouse_press_pos.x() != event.pos().x()
                    or self.mouse_press_pos.y() != event.pos().y()
                )

            self.initial_mouse_scene_pos = None
            self.initial_item_abs_pos = None
            self.mouse_press_pos = None

            if has_moved:
                # Persist via view's save routine (which groups by layer)
                try:
                    self._view._save_text_items_to_db()
                except Exception:
                    # fallback to calling public method
                    try:
                        self._view._save_text_items_to_db()
                    except Exception:
                        pass
            event.accept()
        else:
            return QGraphicsTextItem.mouseReleaseEvent(self, event)


class CustomGraphicsView(
    MediatorMixin,
    SettingsMixin,
    QGraphicsView,
):
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
        return self._canvas_offset

    @canvas_offset.setter
    def canvas_offset(self, value: QPointF):
        self._canvas_offset = value

    @property
    def canvas_offset_x(self) -> float:
        return self.canvas_offset.x()

    @property
    def canvas_offset_y(self) -> float:
        return self.canvas_offset.y()

    @property
    def zero_point(self) -> QPointF:
        return QPointF(0, 0)  # Return QPointF instead of QPoint

    @property
    def grid_compensation_offset(self) -> QPointF:
        """Accumulated viewport compensation offset for grid alignment."""
        return self._grid_compensation_offset

    def load_canvas_offset(self):
        """Load the canvas offset from QSettings."""
        x = self.settings.value("canvas_offset_x", 0.0)  # Default to 0
        y = self.settings.value("canvas_offset_y", 0.0)  # Default to 0
        loaded_offset = QPointF(float(x), float(y))
        self.canvas_offset = loaded_offset

        self.logger.debug(f"Loaded canvas offset from settings: ({x}, {y})")

        # DO NOT call update methods here - let the caller decide when to update
        # This prevents the offset from being modified during load

    def save_canvas_offset(self):
        """Save the canvas offset to QSettings."""
        self.settings.setValue("canvas_offset_x", self.canvas_offset_x)
        self.settings.setValue("canvas_offset_y", self.canvas_offset_y)
        self.logger.debug(
            f"Saved canvas offset: ({self.canvas_offset_x}, {self.canvas_offset_y})"
        )

    @property
    def scene(self) -> Optional[CustomScene]:
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
    def scene(self, value: Optional[CustomScene]):
        self._scene = value

    @property
    def current_tool(self):
        val = getattr(self.application_settings, "current_tool", None)
        try:
            return CanvasToolName(val) if val is not None else None
        except Exception:
            return None

    @property
    def canvas_type(self) -> str:
        return self.property("canvas_type")

    @property
    def __do_show_active_grid_area(self):
        return self.canvas_type in (
            CanvasType.IMAGE.value,
            CanvasType.BRUSH.value,
        )

    @property
    def layers(self) -> List[CanvasLayer]:
        return CanvasLayer.objects.filter_by(visible=True, locked=False)

    @property
    def viewport_center(self) -> QPointF:
        viewport_size = self.viewport().size()
        return QPointF(viewport_size.width() / 2, viewport_size.height() / 2)

    def get_recentered_position(self, width, height) -> Tuple[int, int]:
        viewport_center_x = self.viewport_center.x()
        viewport_center_y = self.viewport_center.y()

        item_center_x = width / 2
        item_center_y = height / 2

        target_x = viewport_center_x - item_center_x
        target_y = viewport_center_y - item_center_y

        snapped_gx, snapped_gy = snap_to_grid(
            self.grid_settings,
            target_x,
            target_y,
            use_floor=False,
        )

        return int(round(snapped_gx)), int(round(snapped_gy))

    def original_item_positions(self) -> Dict[str, QPointF]:
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
            item_rect = scene_item.boundingRect()
            image_width = item_rect.width()
            image_height = item_rect.height()

            pos_x, pos_y = self.get_recentered_position(
                int(image_width), int(image_height)
            )

            DrawingPadSettings.objects.update(
                drawingpad_settings.id,
                x_pos=pos_x,
                y_pos=pos_y,
            )
            scene_item.setPos(pos_x, pos_y)
            original_item_positions[scene_item] = QPointF(pos_x, pos_y)
        return original_item_positions

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
        self.update_active_grid_settings(
            pos_x=pos_x,
            pos_y=pos_y,
        )

        # Clear the scene's position cache completely
        # if hasattr(self.scene, "original_item_positions"):
        #     self.scene.original_item_positions.clear()

        self.save_canvas_offset()

        self.api.art.canvas.update_grid_info(
            {
                "offset_x": self.canvas_offset_x,
                "offset_y": self.canvas_offset_y,
            }
        )

        # Force complete layer refresh from database
        if hasattr(self.scene, "_refresh_layer_display"):
            self.scene._refresh_layer_display()

        # Update display positions
        self.update_active_grid_area_position()

        self.updateImagePositions(self.original_item_positions())

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
            self.grid_item = GridGraphicsItem(self)
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

        # Calculate and set the display position
        display_x = absolute_x - self.canvas_offset_x
        display_y = absolute_y - self.canvas_offset_y
        self.active_grid_area.setPos(display_x, display_y)
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

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.MiddleButton:
            self._middle_mouse_pressed = True
            self.last_pos = event.pos()
            event.accept()
            return
        # Only handle text tool logic if tool is TEXT
        if self.current_tool is CanvasToolName.TEXT:
            scene_pos = self.mapToScene(event.pos())
            # If the user clicked on an existing text item (text, area, handle),
            # let that item receive the event instead of starting a
            # rubberband/drag-to-create operation.
            try:
                items = self.scene.items(scene_pos)
            except Exception:
                items = []

            # Check if any text-related item is under the cursor
            # (filter out grid and active grid area which shouldn't block text creation)
            has_text_item = False
            for item in items:
                if isinstance(item, (QGraphicsTextItem, ResizableTextItem)):
                    has_text_item = True
                    break
                # Check if it's a grid or active grid area that we should ignore
                if isinstance(item, (GridGraphicsItem, ActiveGridArea)):
                    continue
                # Any other item (like handles) should also allow interaction
                if item not in [self.scene.item]:
                    has_text_item = True
                    break

            if has_text_item:
                super().mousePressEvent(event)
                return

            # No existing item under cursor: begin drag-to-create
            self._text_dragging = True
            self._text_drag_start = scene_pos
            try:
                rb = QGraphicsRectItem(QRectF(scene_pos, scene_pos))
                pen = QPen(QColor("white"))
                pen.setStyle(Qt.PenStyle.DashLine)
                rb.setPen(pen)
                rb.setZValue(3000)
                self.scene.addItem(rb)
                self._temp_rubberband = rb
            except Exception:
                self._temp_rubberband = None

            # Begin history transaction for the layer so the add is undoable
            layer_id = self._get_current_selected_layer_id()
            try:
                if self.scene and layer_id is not None:
                    if layer_id not in self.scene._history_transactions:
                        self.scene._begin_layer_history_transaction(
                            layer_id, "text"
                        )
            except Exception:
                pass
            return
        # If not text tool, ensure all text items are not movable/editable
        self._set_text_items_interaction(False)
        super().mousePressEvent(event)

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
                    layer_id = getattr(target, "layer_id", None)
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

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.MiddleButton:
            self.save_canvas_offset()
            self._middle_mouse_pressed = False
            self.last_pos = None

            # After releasing middle mouse button, trigger a cursor update
            # Pass a fake enter event to the scene to refresh the cursor
            if self.scene:
                # Create a simple "dummy" event just to trigger cursor update
                class SimpleEvent:
                    def __init__(self):
                        pass

                    def type(self):
                        return QEvent.Type.Enter

                # Tell the scene to update the cursor based on current tool
                self.scene.handle_cursor(SimpleEvent(), True)

            event.accept()
            return
        # Handle completing a text-area drag
        if self.current_tool is CanvasToolName.TEXT and self._text_dragging:
            end_pos = self.mapToScene(event.pos())
            start = self._text_drag_start
            rb = self._temp_rubberband
            # remove the temporary rubberband
            try:
                if rb and rb.scene() == self.scene:
                    self.scene.removeItem(rb)
            except Exception:
                pass
            self._temp_rubberband = None
            self._text_dragging = False

            # If the drag was very small, create inline text at the click
            if start is None:
                return
            dx = abs(end_pos.x() - start.x())
            dy = abs(end_pos.y() - start.y())
            layer_id = self._get_current_selected_layer_id()
            try:
                if dx < 6 and dy < 6:
                    # create inline text
                    self._add_text_item_inline(start)
                else:
                    # create a resizable text area
                    left = min(start.x(), end_pos.x())
                    top = min(start.y(), end_pos.y())
                    w = abs(end_pos.x() - start.x())
                    h = abs(end_pos.y() - start.y())
                    rect = QRectF(left, top, w, h)
                    area = ResizableTextItem(self, rect)
                    area.setZValue(2000)
                    # Focus the internal text for editing
                    try:
                        area.text_item.setFocus()
                        # Bind inspector to child text item
                        if self._text_inspector:
                            self._text_inspector.bind_to(area.text_item)
                    except Exception:
                        pass
                    # add to scene and tracking lists
                    try:
                        self.scene.addItem(area)
                        self._text_items.append(area)
                        self._text_item_layer_map[area] = layer_id
                        self._editing_text_item = area.text_item
                        # make child handlers
                        area.text_item.focusOutEvent = (
                            self._make_text_focus_out_handler(area.text_item)
                        )
                        area.text_item.keyPressEvent = (
                            self._make_text_key_press_handler(area.text_item)
                        )
                        area.text_item.itemChange = (
                            self._make_text_item_change_handler(area.text_item)
                        )
                        # ensure the text width is set so it wraps
                        area.text_item.setTextWidth(area.rect().width())
                        # Persist
                        self._save_text_items_to_db()
                    except Exception:
                        self.logger.exception("Failed creating text area")

            finally:
                # Commit the transaction after saving
                try:
                    if self.scene and layer_id is not None:
                        self.scene._commit_layer_history_transaction(
                            layer_id, "text"
                        )
                except Exception:
                    pass
            return
        super().mouseReleaseEvent(event)

    def mouseMoveEvent(self, event):
        if self._middle_mouse_pressed:
            delta = event.pos() - self.last_pos
            self.canvas_offset -= delta
            self.last_pos = event.pos()
            self.api.art.canvas.update_grid_info(
                {
                    "offset_x": self.canvas_offset_x,
                    "offset_y": self.canvas_offset_y,
                }
            )
            if not self._pan_update_timer.isActive():
                self._pan_update_timer.start(1)
            else:
                self._pending_pan_event = True
            event.accept()
            return
        # Update rubberband during text drag
        if self.current_tool is CanvasToolName.TEXT and self._text_dragging:
            if not self._temp_rubberband:
                return
            scene_pos = self.mapToScene(event.pos())
            start = self._text_drag_start
            if start is None:
                return
            left = min(start.x(), scene_pos.x())
            top = min(start.y(), scene_pos.y())
            w = abs(scene_pos.x() - start.x())
            h = abs(scene_pos.y() - start.y())
            try:
                self._temp_rubberband.setRect(QRectF(left, top, w, h))
            except Exception:
                pass
            event.accept()
            return
        super().mouseMoveEvent(event)

    def keyPressEvent(self, event):
        # Support Delete key to remove selected text items from the canvas
        if event.key() == Qt.Key.Key_Delete:
            # Collect selected text items
            to_remove = [it for it in self._text_items if it.isSelected()]
            if to_remove:
                # Group by layer and begin a transaction per layer
                layers = {}
                for item in to_remove:
                    layer_id = self._text_item_layer_map.get(item)
                    layers.setdefault(layer_id, []).append(item)

                for layer_id, items in layers.items():
                    try:
                        if self.scene and layer_id is not None:
                            if (
                                layer_id
                                not in self.scene._history_transactions
                            ):
                                self.scene._begin_layer_history_transaction(
                                    layer_id, "text"
                                )
                    except Exception:
                        pass

                    for item in items:
                        self._remove_text_item(item, manage_transaction=False)

                    try:
                        if self.scene and layer_id is not None:
                            self.scene._commit_layer_history_transaction(
                                layer_id, "text"
                            )
                    except Exception:
                        pass
                return
        super().keyPressEvent(event)

    def _do_pan_update(self):
        self.update_active_grid_area_position()
        self.updateImagePositions()
        self.draw_grid()
        if self._pending_pan_event:
            self._pending_pan_event = False
            self._pan_update_timer.start(1)

    def showEvent(self, event):
        super().showEvent(event)
        # if not self._initialized:
        # Set restoration flag to prevent resize compensation during initial load
        self._is_restoring_state = True

        # Load offset first - this ONLY sets the canvas_offset to the saved value
        self.load_canvas_offset()

        # Store the loaded offset to restore it after any operations
        loaded_offset = QPointF(self.canvas_offset.x(), self.canvas_offset.y())

        # Set up the scene (grid, etc.) - DO NOT let these change the offset
        self.do_draw(True)
        self.toggle_drag_mode()
        self.set_canvas_color(self.scene)

        # Restore the offset after do_draw
        self.canvas_offset = loaded_offset

        # Show the active grid area using loaded offset
        self.show_active_grid_area()

        # Restore the offset after show_active_grid_area
        self.canvas_offset = loaded_offset

        # Update viewport size tracking without adjusting offset
        self._last_viewport_size = self.viewport().size()

        # Now update positions with the restored offset
        self.update_active_grid_area_position()
        self.updateImagePositions()

        # FORCE the offset back to loaded value after position updates
        self.canvas_offset = loaded_offset

        # Restore text items on load
        try:
            self._restore_text_items_from_db()
        except Exception:
            self.logger.exception("Failed to restore text items on showEvent")

        # Final offset restoration
        self.canvas_offset = loaded_offset

        self._initialized = True

        # Use a short delay to allow the window to fully settle before
        # re-enabling resize compensation
        QTimer.singleShot(500, self._finish_state_restoration)

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

    def resizeEvent(self, event):
        """Handle viewport resize to keep canvas centered without changing offset values.

        When the viewport resizes, the visual center shifts but the canvas offset
        (which represents the user's pan position) should remain unchanged. We compensate
        by adjusting the stored absolute positions of items to account for the viewport
        center change.
        """
        super().resizeEvent(event)

        # Skip compensation during initial state restoration
        if self._is_restoring_state or not self._initialized:
            self._last_viewport_size = self.viewport().size()
            return

        # Calculate the change in viewport center
        old_size = self._last_viewport_size
        new_size = self.viewport().size()

        # If size hasn't actually changed, no need to update
        if old_size == new_size:
            return

        # Calculate the shift in viewport center
        old_center_x = old_size.width() / 2
        old_center_y = old_size.height() / 2
        new_center_x = new_size.width() / 2
        new_center_y = new_size.height() / 2

        center_shift_x = new_center_x - old_center_x
        center_shift_y = new_center_y - old_center_y

        # Apply the compensation by adjusting the stored absolute positions
        # This keeps the canvas_offset unchanged while shifting the visual positions
        self._apply_viewport_compensation(center_shift_x, center_shift_y)

        # Update the tracked viewport size for next resize
        self._last_viewport_size = new_size

        # Redraw the grid with new viewport size
        self.draw_grid()

    def _apply_viewport_compensation(self, shift_x: float, shift_y: float):
        """Apply viewport center compensation by adjusting stored absolute positions.

        This method shifts the absolute positions of items so they appear to stay
        centered relative to the viewport, without changing the canvas_offset value.
        """
        if not self.scene:
            return

        # Skip if the shift is negligible
        if abs(shift_x) < 0.5 and abs(shift_y) < 0.5:
            return

        # Adjust the grid compensation offset
        # This shifts the grid origin to maintain alignment with the viewport center
        self._grid_compensation_offset = QPointF(
            self._grid_compensation_offset.x() + shift_x,
            self._grid_compensation_offset.y() + shift_y,
        )

        # Adjust the active grid area absolute position
        if self.active_grid_area:
            current_abs_x = self.active_grid_settings.pos_x or 0
            current_abs_y = self.active_grid_settings.pos_y or 0
            new_abs_x = current_abs_x + shift_x
            new_abs_y = current_abs_y + shift_y
            self.update_active_grid_settings(pos_x=new_abs_x, pos_y=new_abs_y)

        # Adjust layer absolute positions
        layers = CanvasLayer.objects.order_by("order").all()
        for layer in layers:
            drawing_pad = DrawingPadSettings.objects.filter_by_first(
                layer_id=layer.id
            )
            if drawing_pad:
                current_x = drawing_pad.x_pos or 0
                current_y = drawing_pad.y_pos or 0
                new_x = current_x + shift_x
                new_y = current_y + shift_y
                self.update_drawing_pad_settings(
                    layer_id=layer.id, x_pos=new_x, y_pos=new_y
                )

        # Update the scene's cached original positions to match
        if hasattr(self.scene, "original_item_positions"):
            updated_positions = {}
            for item, old_pos in self.scene.original_item_positions.items():
                updated_positions[item] = QPointF(
                    old_pos.x() + shift_x, old_pos.y() + shift_y
                )
            self.scene.original_item_positions = updated_positions

        # Now update the visual positions (these use canvas_offset which hasn't changed)
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

    def toggle_drag_mode(self):
        self.setDragMode(QGraphicsView.DragMode.NoDrag)

    def update_active_grid_area_position(self):
        if self.active_grid_area:
            pos = self.active_grid_settings.pos
            pos_x = pos[0] - self.canvas_offset_x
            pos_y = pos[1] - self.canvas_offset_y
            self.active_grid_area.setPos(pos_x, pos_y)

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

    def get_cached_cursor(self, tool, size):
        key = (tool, size)
        if key not in self._cursor_cache:
            if tool in (CanvasToolName.BRUSH, CanvasToolName.ERASER):
                # You may want to use different colors for eraser
                cursor = circle_cursor(
                    Qt.GlobalColor.white, Qt.GlobalColor.transparent, size
                )
                self._cursor_cache[key] = cursor
        return self._cursor_cache.get(key)

    def _update_cursor(self, event=None, current_tool=None, apply_cursor=True):
        # event: QEvent or similar, current_tool: CanvasToolName
        # apply_cursor: bool
        if current_tool is None:
            current_tool = self.current_tool
        cursor = None
        if apply_cursor:
            try:
                if (
                    event
                    and hasattr(event, "button")
                    and event.button() == Qt.MouseButton.MiddleButton
                ):
                    cursor = Qt.CursorShape.ClosedHandCursor
                elif current_tool in (
                    CanvasToolName.BRUSH,
                    CanvasToolName.ERASER,
                ):
                    size = getattr(self, "brush_settings", None)
                    size = size.size if size else 32
                    cursor = self.get_cached_cursor(current_tool, size)
                elif current_tool is CanvasToolName.TEXT:
                    cursor = Qt.CursorShape.IBeamCursor
                elif current_tool in (
                    CanvasToolName.ACTIVE_GRID_AREA,
                    CanvasToolName.MOVE,
                ):
                    if (
                        event
                        and hasattr(event, "buttons")
                        and event.buttons() == Qt.MouseButton.LeftButton
                    ):
                        cursor = Qt.CursorShape.ClosedHandCursor
                    else:
                        cursor = Qt.CursorShape.OpenHandCursor
                elif current_tool is CanvasToolName.NONE:
                    cursor = Qt.CursorShape.ArrowCursor
            except Exception:
                self.logger.exception("Failed to determine cursor")

        # Apply cursor if determined
        try:
            if cursor is not None:
                self.setCursor(cursor)
        except Exception:
            pass

    def _find_text_item_at(self, pos):
        if not self.scene:
            return None
        items = self.scene.items(pos)
        for item in items:
            if isinstance(item, QGraphicsTextItem):
                return item
        return None

    def _add_text_item_inline(self, pos: QPointF):
        """Create a new QGraphicsTextItem at scene position and start editing inline."""
        if not self.scene:
            return

        text_item = DraggableTextItem(self)
        text_item.setPlainText("")
        text_item.setTextInteractionFlags(Qt.TextEditorInteraction)
        text_item.setFlag(QGraphicsTextItem.ItemIsMovable, True)
        text_item.setFlag(QGraphicsTextItem.ItemIsSelectable, True)
        text_item.setFlag(QGraphicsTextItem.ItemIsFocusable, True)
        text_item.setPos(pos)
        text_item.setZValue(2000)  # Above images (which use ~1000)
        text_item.setDefaultTextColor(QColor("white"))
        text_item.setFont(self._get_default_text_font())
        text_item.setFlag(QGraphicsTextItem.ItemSendsGeometryChanges, True)
        text_item.itemChange = self._make_text_item_change_handler(text_item)
        text_item.focusOutEvent = self._make_text_focus_out_handler(text_item)
        text_item.keyPressEvent = self._make_text_key_press_handler(text_item)

        self.scene.addItem(text_item)
        self._text_items.append(text_item)
        # Associate with currently selected layer
        layer_id = self._get_current_selected_layer_id()
        self._text_item_layer_map[text_item] = layer_id

        text_item.setFocus()
        self._editing_text_item = text_item
        # Bind inspector
        if self._text_inspector:
            self._text_inspector.bind_to(text_item)

        self._save_text_items_to_db()

    def _edit_text_item(self, item):
        # Only allow editing if text tool is active
        if self.current_tool is CanvasToolName.TEXT:
            item.setTextInteractionFlags(Qt.TextEditorInteraction)
            item.setFlag(QGraphicsTextItem.ItemIsMovable, True)
            item.setFlag(QGraphicsTextItem.ItemIsSelectable, True)
            item.setFocus()
            self._editing_text_item = item
            # Bind inspector to this item
            if self._text_inspector:
                self._text_inspector.bind_to(item)

    def _make_text_focus_out_handler(self, item):
        def handler(event):
            # If focus moved into the inspector widget (or its children), keep
            # the inspector bound so clicking controls doesn't cause the
            # inspector to disappear.
            try:
                fw = QApplication.focusWidget()
                if self._text_inspector is not None and fw is not None:
                    try:
                        if (
                            self._text_inspector.isAncestorOf(fw)
                            or fw is self._text_inspector
                        ):
                            # Don't unbind; leave the text interaction flags alone
                            QGraphicsTextItem.focusOutEvent(item, event)
                            return
                    except Exception:
                        # If any failure occurs checking ancestry, fall back to
                        # default behavior below
                        pass

            except Exception:
                pass

            item.setTextInteractionFlags(Qt.NoTextInteraction)
            self._editing_text_item = None
            self._save_text_items_to_db()
            # Unbind inspector when editing finishes
            if self._text_inspector:
                self._text_inspector.bind_to(None)
            QGraphicsTextItem.focusOutEvent(item, event)

        return handler

    def _make_text_key_press_handler(self, item):
        def handler(event):
            if event.key() == Qt.Key.Key_Delete:
                self._remove_text_item(item)
            else:
                QGraphicsTextItem.keyPressEvent(item, event)

        return handler

    def _make_text_item_change_handler(self, item):
        def handler(change, value):
            if change == QGraphicsTextItem.ItemPositionChange:
                self._save_text_items_to_db()
            return QGraphicsTextItem.itemChange(item, change, value)

        return handler

    def _remove_text_item(
        self, item, *, manage_transaction: bool = True
    ) -> None:
        layer_id = self._text_item_layer_map.get(item)
        if manage_transaction:
            try:
                if self.scene and layer_id is not None:
                    if layer_id not in self.scene._history_transactions:
                        self.scene._begin_layer_history_transaction(
                            layer_id, "text"
                        )
            except Exception:
                pass

        try:
            if hasattr(item, "scene") and item.scene():
                item.scene().removeItem(item)
        except Exception:
            pass

        if item in self._text_items:
            self._text_items.remove(item)
        if item in self._text_item_layer_map:
            del self._text_item_layer_map[item]

        editing = getattr(self, "_editing_text_item", None)
        if editing is item or getattr(item, "text_item", None) is editing:
            self._editing_text_item = None
        if self._text_inspector:
            try:
                self._text_inspector.bind_to(None)
            except Exception:
                pass

        self._save_text_items_to_db()

        if manage_transaction:
            try:
                if self.scene and layer_id is not None:
                    self.scene._commit_layer_history_transaction(
                        layer_id, "text"
                    )
            except Exception:
                pass

    def _get_default_text_font(self):
        font = QFont()
        font.setPointSize(18)
        font.setFamily("Arial")
        return font

    def _save_text_items_to_db(self):
        # Save all text items to the database (via application_settings or similar)
        # Group text items by associated layer and save per-layer
        layer_buckets: Dict[Optional[int], list] = {}
        for item in self._text_items:
            layer_id = self._text_item_layer_map.get(item)
            if layer_id not in layer_buckets:
                layer_buckets[layer_id] = []
            # Two kinds of items: inline QGraphicsTextItem or ResizableTextItem
            try:
                if isinstance(item, ResizableTextItem):
                    d = item.to_persist_dict()
                    layer_buckets[layer_id].append(d)
                elif isinstance(item, QGraphicsTextItem):
                    abs_x = int(item.pos().x() + self.canvas_offset_x)
                    abs_y = int(item.pos().y() + self.canvas_offset_y)
                    layer_buckets[layer_id].append(
                        {
                            "type": "inline",
                            "text": item.toPlainText(),
                            "x": abs_x,
                            "y": abs_y,
                            "color": item.defaultTextColor().name(),
                            "font": item.font().toString(),
                        }
                    )
                else:
                    # Unknown item type: try best-effort extraction
                    abs_x = int(item.pos().x() + self.canvas_offset_x)
                    abs_y = int(item.pos().y() + self.canvas_offset_y)
                    text = getattr(item, "toPlainText", lambda: "")()
                    color = "white"
                    try:
                        color = item.defaultTextColor().name()
                    except Exception:
                        pass
                    font = ""
                    try:
                        font = item.font().toString()
                    except Exception:
                        pass
                    layer_buckets[layer_id].append(
                        {
                            "type": "inline",
                            "text": text,
                            "x": abs_x,
                            "y": abs_y,
                            "color": color,
                            "font": font,
                        }
                    )
            except Exception:
                self.logger.exception("Failed serializing text item for DB")

        # Persist each layer's text items JSON into DrawingPadSettings.text_items
        for layer_id, items in layer_buckets.items():
            try:
                json_text = json.dumps(items)
                # Use update_drawing_pad_settings with explicit layer_id
                self.update_drawing_pad_settings(
                    layer_id=layer_id, text_items=json_text
                )
            except Exception:
                self.logger.exception(
                    "Failed to save text items for layer %s", layer_id
                )

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

    def _restore_text_items_from_db(self):
        # Restore text items from per-layer DrawingPadSettings.text_items
        self._clear_text_items()
        try:
            # iterate through layers and load their text_items JSON
            for layer in CanvasLayer.objects.order_by("order").all():
                settings = DrawingPadSettings.objects.filter_by_first(
                    layer_id=layer.id
                )
                if not settings:
                    continue
                raw = getattr(settings, "text_items", None)
                if not raw:
                    continue
                try:
                    data_list = json.loads(raw)
                except Exception:
                    data_list = []

                for data in data_list:
                    text = data.get("text", "")
                    x = data.get("x", 0)
                    y = data.get("y", 0)
                    color = QColor(data.get("color", "white"))
                    font = QFont()
                    try:
                        font.fromString(data.get("font", ""))
                    except Exception:
                        font = self._get_default_text_font()
                    # Distinguish between inline and area types
                    item_type = data.get("type", "inline")
                    if item_type == "area":
                        # Restore a ResizableTextItem with provided w/h
                        w = data.get("w", 100)
                        h = data.get("h", 40)
                        display_x = x - int(self.canvas_offset_x)
                        display_y = y - int(self.canvas_offset_y)
                        rect = QRectF(display_x, display_y, w, h)
                        area = ResizableTextItem(self, rect)
                        area.text_item.setPlainText(text)
                        area.text_item.setDefaultTextColor(color)
                        area.text_item.setFont(font)
                        area.setZValue(2000)
                        # Bind handlers to the text child so focus/keys persist
                        area.text_item.focusOutEvent = (
                            self._make_text_focus_out_handler(area.text_item)
                        )
                        area.text_item.keyPressEvent = (
                            self._make_text_key_press_handler(area.text_item)
                        )
                        area.text_item.itemChange = (
                            self._make_text_item_change_handler(area.text_item)
                        )
                        self.scene.addItem(area)
                        self._text_items.append(area)
                        self._text_item_layer_map[area] = layer.id
                    else:
                        text_item = DraggableTextItem(self)
                        text_item.setPlainText(text)
                        # Stored x/y are absolute coordinates; convert to display
                        # position by subtracting the current canvas offset.
                        display_x = x - int(self.canvas_offset_x)
                        display_y = y - int(self.canvas_offset_y)
                        text_item.setPos(QPointF(display_x, display_y))
                        text_item.setDefaultTextColor(color)
                        text_item.setFont(font)
                        text_item.setFlag(
                            QGraphicsTextItem.ItemIsMovable, True
                        )
                        text_item.setFlag(
                            QGraphicsTextItem.ItemIsSelectable, True
                        )
                        text_item.setFlag(
                            QGraphicsTextItem.ItemIsFocusable, True
                        )
                        text_item.setFlag(
                            QGraphicsTextItem.ItemSendsGeometryChanges, True
                        )
                        text_item.setZValue(2000)
                        text_item.focusOutEvent = (
                            self._make_text_focus_out_handler(text_item)
                        )
                        text_item.keyPressEvent = (
                            self._make_text_key_press_handler(text_item)
                        )
                        text_item.itemChange = (
                            self._make_text_item_change_handler(text_item)
                        )
                        self.scene.addItem(text_item)
                        self._text_items.append(text_item)
                        self._text_item_layer_map[text_item] = layer.id
        except Exception:
            self.logger.exception("Failed to restore text items from DB")

    # (per-layer restore implementation above is the authoritative one)

    def _clear_text_items(self):
        for item in self._text_items:
            self.scene.removeItem(item)
        self._text_items.clear()
        self._text_item_layer_map.clear()

    def _set_text_items_interaction(self, enable: bool):
        # Enable/disable moving/editing for all text items
        for item in self._text_items:
            if isinstance(item, ResizableTextItem):
                item.set_interaction_enabled(enable)
                continue

            if enable:
                item.setFlag(
                    QGraphicsTextItem.GraphicsItemFlag.ItemIsMovable, True
                )
                item.setFlag(
                    QGraphicsTextItem.GraphicsItemFlag.ItemIsSelectable, True
                )
                item.setTextInteractionFlags(
                    Qt.TextInteractionFlag.TextEditorInteraction
                )
            else:
                item.setFlag(
                    QGraphicsTextItem.GraphicsItemFlag.ItemIsMovable, False
                )
                item.setFlag(
                    QGraphicsTextItem.GraphicsItemFlag.ItemIsSelectable, False
                )
                try:
                    item.setTextInteractionFlags(
                        Qt.TextInteractionFlag.NoTextInteraction
                    )
                except AttributeError:
                    pass
