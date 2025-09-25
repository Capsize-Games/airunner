from typing import List, Optional, Dict
import time

from PySide6.QtCore import (
    QPointF,
    QPoint,
    Qt,
    QEvent,
    QSize,
    QTimer,
)
from PySide6.QtGui import QMouseEvent, QColor, QBrush, QFont
from PySide6.QtWidgets import (
    QGraphicsView,
    QGraphicsItemGroup,
    QGraphicsScene,
    QGraphicsTextItem,
    QInputDialog,
)

from airunner.components.art.data.canvas_layer import CanvasLayer
from airunner.components.art.data.drawingpad_settings import DrawingPadSettings
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


class CustomGraphicsView(
    MediatorMixin,
    SettingsMixin,
    QGraphicsView,
):
    def __init__(self, *args, **kwargs):
        super().__init__()
        self._recent_event_size = None
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
        self.canvas_offset = QPointF(
            0, 0
        )  # Explicitly use QPointF, not QPoint
        self.settings = get_qsettings()
        self._middle_mouse_pressed: bool = False
        self.grid_item = None
        self._text_items = []  # Store references to QGraphicsTextItem
        self._editing_text_item = None

        # Add settings to handle negative coordinates properly
        self.setAlignment(
            Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft
        )  # Set once here
        self._last_viewport_size = self.viewport().size()  # Track last size
        self.setViewportUpdateMode(
            QGraphicsView.ViewportUpdateMode.BoundingRectViewportUpdate
        )

        # Use setOptimizationFlags directly instead of the enum that doesn't exist in your PySide6 version
        self.setOptimizationFlags(
            QGraphicsView.OptimizationFlag.DontAdjustForAntialiasing
            | QGraphicsView.OptimizationFlag.DontSavePainterState
        )

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

        # Improved resize throttling
        self._time_since_last_resize = 0
        self._resize_timer = QTimer()
        self._resize_timer.setSingleShot(False)
        self._resize_timer.timeout.connect(self._handle_deferred_resize)
        self._resize_timer.setInterval(1)
        self._resize_data = None
        self._is_resizing = False

        self._cursor_cache = {}
        self._current_cursor = None

    @property
    def zero_point(self) -> QPointF:
        return QPointF(0, 0)  # Return QPointF instead of QPoint

    def load_canvas_offset(self):
        """Load the canvas offset from QSettings."""
        x = self.settings.value("canvas_offset_x", 0.0)  # Default to 0
        y = self.settings.value("canvas_offset_y", 0.0)  # Default to 0
        self.canvas_offset = QPointF(float(x), float(y))

        # Update positions after loading offset
        self.update_active_grid_area_position()
        self.updateImagePositions()
        self.do_draw()

    def save_canvas_offset(self):
        """Save the canvas offset to QSettings."""
        self.settings.setValue("canvas_offset_x", self.canvas_offset.x())
        self.settings.setValue("canvas_offset_y", self.canvas_offset.y())

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
    def __can_draw_grid(self):
        return self.grid_settings.show_grid and self.canvas_type in (
            CanvasType.IMAGE.value,
            CanvasType.BRUSH.value,
        )

    @property
    def layers(self) -> List[CanvasLayer]:
        return CanvasLayer.objects.filter_by(visible=True, locked=False)

    def on_recenter_grid_signal(self):
        """Center the grid in the viewport with the active grid area's CENTER at the grid origin."""
        # 1. Calculate center of viewport
        viewport_size = self.viewport().size()
        viewport_center_x = viewport_size.width() / 2
        viewport_center_y = viewport_size.height() / 2

        # 2. To center the grid origin (0,0) in the viewport, set canvas offset to negative viewport center
        # This makes scene coordinate (0,0) appear at the center of the viewport
        self.canvas_offset = QPointF(-viewport_center_x, -viewport_center_y)
        self.save_canvas_offset()

        # 3. Calculate the position needed to center the active grid area on the origin (0,0)
        # We want the CENTER of the active grid area to be at (0,0), not its top-left corner
        grid_width = self.application_settings.working_width
        grid_height = self.application_settings.working_height

        # Position needs to be negative half-dimensions to center it
        pos_x = -grid_width / 2
        pos_y = -grid_height / 2

        # 4. Set active grid area to this centered position
        self.update_active_grid_settings(pos_x=int(pos_x), pos_y=int(pos_y))

        # 5. If there's an image in the scene, update its position to match the active grid area
        if self.scene and hasattr(self.scene, "item") and self.scene.item:
            # Store the same absolute position for the image as we did for the active grid area
            self.scene.original_item_positions[self.scene.item] = QPointF(
                pos_x, pos_y
            )

        # 6. Update all layer items to the same centered position
        if self.scene and hasattr(self.scene, "_layer_items"):
            for layer_id, layer_item in self.scene._layer_items.items():
                # Update the original position tracking
                self.scene.original_item_positions[layer_item] = QPointF(
                    pos_x, pos_y
                )

                # Update the corresponding DrawingPadSettings in the database
                try:
                    from airunner.components.art.data.drawingpad_settings import (
                        DrawingPadSettings,
                    )

                    results = DrawingPadSettings.objects.filter_by(
                        layer_id=layer_id
                    )
                    if results:
                        settings = results[0]
                        # Update the database with the new centered position
                        self.update_drawing_pad_settings(
                            x_pos=int(pos_x), y_pos=int(pos_y)
                        )
                except Exception as e:
                    print(
                        f"Failed to update DrawingPadSettings for layer {layer_id}: {e}"
                    )

            # Trigger visual refresh of all layer positions
            self.scene._refresh_layer_display()

        # 7. Update all display positions based on new offset
        self.updateImagePositions()
        self.update_active_grid_area_position()
        self.update_drawing_pad_settings(x_pos=int(pos_x), y_pos=int(pos_y))
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
                self.do_draw()
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
            self.active_grid_area.setZValue(10)  # Ensure high visibility
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
                + self.canvas_offset.x()
                - (self.application_settings.working_width / 2)
            )
            absolute_y = (
                viewport_center_y
                + self.canvas_offset.y()
                - (self.application_settings.working_height / 2)
            )

            # Save this initial absolute position
            self.update_active_grid_settings(
                pos_x=int(round(absolute_x)), pos_y=int(round(absolute_y))
            )
            self.settings.sync()

        # Calculate and set the display position
        display_x = absolute_x - self.canvas_offset.x()
        display_y = absolute_y - self.canvas_offset.y()
        self.active_grid_area.setPos(display_x, display_y)

    def update_active_grid_area_position(
        self, _message=None
    ):  # Accept optional message from signal
        if self.active_grid_area:
            # Read the definitive absolute position from settings
            absolute_x = self.active_grid_settings.pos_x
            absolute_y = self.active_grid_settings.pos_y

            # Handle potential None values (shouldn't happen after show_active_grid_area)
            if absolute_x is None:
                absolute_x = 0
            if absolute_y is None:
                absolute_y = 0

            # Calculate the display position based on the current canvas offset
            display_x = absolute_x - self.canvas_offset.x()
            display_y = absolute_y - self.canvas_offset.y()

            # Set the item's display position
            self.active_grid_area.setPos(display_x, display_y)

    def on_zoom_level_changed_signal(self):
        transform = self.zoom_handler.on_zoom_level_changed()

        # Set the transform
        self.setTransform(transform)

        # Redraw lines
        self.do_draw()

    def resizeEvent(self, event):
        self._time_since_last_resize = time.time()
        self._recent_event_size = event.size()
        super().resizeEvent(event)
        # start the resize timer if it is not already running
        if not self._resize_timer.isActive():
            self._resize_timer.start()

    def _handle_deferred_resize(self):
        if self._recent_event_size is None:
            if time.time() - self._time_since_last_resize >= 1:
                self._resize_timer.stop()
            return
        size = self._recent_event_size
        self._recent_event_size = None
        width = size.width()
        height = size.height()
        canvas_container_size = self.viewport().size()
        screen_size = self.screen().availableGeometry().size()
        screen_width = screen_size.width() - 64
        screen_height = screen_size.height() - 160
        x = (screen_width - width) / 2
        y = (screen_height - height) / 2
        self.scene.setSceneRect(
            x,
            y,
            canvas_container_size.width(),
            canvas_container_size.height(),
        )
        # Store resize data
        self._resize_data = {
            "new_size": self.viewport().size(),
            "old_size": canvas_container_size,
        }
        # Center the grid in the viewport with the active grid area's CENTER at the grid origin.
        viewport_size = self.viewport().size()
        viewport_center_x = viewport_size.width() / 2
        viewport_center_y = viewport_size.height() / 2
        self.canvas_offset = QPointF(-viewport_center_x, -viewport_center_y)
        self.save_canvas_offset()
        self.updateImagePositions()
        self.do_draw(force_draw=True)

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
            item = self._find_text_item_at(scene_pos)
            if item:
                # Select and edit existing text item
                self._edit_text_item(item)
                return
            else:
                # Add new text item
                self._add_text_item(scene_pos)
                return
        # If not text tool, ensure all text items are not movable/editable
        self._set_text_items_interaction(False)
        super().mousePressEvent(event)

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
        super().mouseReleaseEvent(event)

    def mouseMoveEvent(self, event):
        if self._middle_mouse_pressed:
            delta = event.pos() - self.last_pos
            self.canvas_offset -= delta
            self.last_pos = event.pos()
            if not self._pan_update_timer.isActive():
                self._pan_update_timer.start(1)
            else:
                self._pending_pan_event = True
            event.accept()
            return
        super().mouseMoveEvent(event)

    def _do_pan_update(self):
        self.update_active_grid_area_position()
        self.updateImagePositions()
        self.draw_grid()
        if self._pending_pan_event:
            self._pending_pan_event = False
            self._pan_update_timer.start(1)

    def showEvent(self, event):
        super().showEvent(event)
        if not self._initialized:
            # Load offset first
            self.load_canvas_offset()

            # Set up the scene (grid, etc.)
            self.do_draw(True)
            self.toggle_drag_mode()
            self.set_canvas_color(self.scene)

            # Show the active grid area using loaded offset
            self.show_active_grid_area()
            self.scene.initialize_image()
            self.updateImagePositions()
            # self._restore_text_items_from_db()  # Restore text items on load
            self._initialized = True

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

    def toggle_drag_mode(self):
        self.setDragMode(QGraphicsView.DragMode.NoDrag)

    def handle_pan_canvas(self, event: QMouseEvent):
        if self._middle_mouse_pressed:
            delta = event.pos() - self.last_pos

            self.canvas_offset -= delta
            self.last_pos = event.pos()

            # Update display positions based on the NEW offset
            self.update_active_grid_area_position()
            self.updateImagePositions()
            self.draw_grid()

    def update_active_grid_area_position(self):
        if self.active_grid_area:
            pos = self.active_grid_settings.pos
            pos_x = pos[0] - self.canvas_offset.x()
            pos_y = pos[1] - self.canvas_offset.y()
            if self.active_grid_area:
                self.active_grid_area.setPos(pos_x, pos_y)

    def updateImagePositions(self):
        """Update positions of all images in the scene based on canvas offset."""
        if not self.scene:
            return

        # Use the scene's update_image_position method which handles both
        # the old single-item system and the new layer system
        self.scene.update_image_position(self.canvas_offset)

        # Force entire viewport update to handle negative coordinates
        self.viewport().update()

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
        # Update image positions based on current canvas offset
        self.updateImagePositions()

        # Ensure the scene updates to show the new image correctly
        self.update_scene()

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
            if (
                event
                and hasattr(event, "button")
                and event.button() == Qt.MouseButton.MiddleButton
            ):
                cursor = Qt.CursorShape.ClosedHandCursor
            elif current_tool in (CanvasToolName.BRUSH, CanvasToolName.ERASER):
                size = getattr(self, "brush_settings", None)
                size = size.size if size else 32
                cursor = self.get_cached_cursor(current_tool, size)
            elif current_tool is CanvasToolName.TEXT:
                cursor = Qt.CursorShape.IBeamCursor
            elif current_tool is CanvasToolName.ACTIVE_GRID_AREA:
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
        else:
            cursor = Qt.CursorShape.ArrowCursor
        if self._current_cursor != cursor:
            self.setCursor(cursor)
            self._current_cursor = cursor

    def on_undo_button_clicked(self):
        self.api.art.canvas.undo()
        # Do not sync image to grid area; keep image at its last location

    def on_redo_button_clicked(self):
        self.api.art.canvas.redo()
        # Do not sync image to grid area; keep image at its last location

    def _find_text_item_at(self, pos):
        if not self.scene:
            return None
        items = self.scene.items(pos)
        for item in items:
            if isinstance(item, QGraphicsTextItem):
                return item
        return None

    def _add_text_item(self, pos):
        if not self.scene:
            return
        text, ok = QInputDialog.getText(self, "Add Text", "Enter text:")
        if ok and text:
            text_item = QGraphicsTextItem(text)
            text_item.setTextInteractionFlags(Qt.TextEditorInteraction)
            text_item.setFlag(QGraphicsTextItem.ItemIsMovable, True)
            text_item.setFlag(QGraphicsTextItem.ItemIsSelectable, True)
            text_item.setFlag(QGraphicsTextItem.ItemIsFocusable, True)
            text_item.setPos(pos)
            self.scene.addItem(text_item)
            self._text_items.append(text_item)
            text_item.focusOutEvent = self._make_text_focus_out_handler(
                text_item
            )
            text_item.keyPressEvent = self._make_text_key_press_handler(
                text_item
            )
            text_item.setFocus()
            self._editing_text_item = text_item
            text_item.setZValue(20)
            text_item.setDefaultTextColor(QColor("white"))
            text_item.setFont(self._get_default_text_font())
            text_item.setFlag(QGraphicsTextItem.ItemSendsGeometryChanges, True)
            text_item.itemChange = self._make_text_item_change_handler(
                text_item
            )
            self._save_text_items_to_db()

    def _edit_text_item(self, item):
        # Only allow editing if text tool is active
        if self.current_tool is CanvasToolName.TEXT:
            item.setTextInteractionFlags(Qt.TextEditorInteraction)
            item.setFlag(QGraphicsTextItem.ItemIsMovable, True)
            item.setFlag(QGraphicsTextItem.ItemIsSelectable, True)
            item.setFocus()
            self._editing_text_item = item

    def _make_text_focus_out_handler(self, item):
        def handler(event):
            item.setTextInteractionFlags(Qt.NoTextInteraction)
            self._editing_text_item = None
            self._save_text_items_to_db()
            QGraphicsTextItem.focusOutEvent(item, event)

        return handler

    def _make_text_key_press_handler(self, item):
        def handler(event):
            if event.key() == Qt.Key.Key_Delete:
                self.scene.removeItem(item)
                if item in self._text_items:
                    self._text_items.remove(item)
                self._save_text_items_to_db()
                self._editing_text_item = None
            else:
                QGraphicsTextItem.keyPressEvent(item, event)

        return handler

    def _make_text_item_change_handler(self, item):
        def handler(change, value):
            if change == QGraphicsTextItem.ItemPositionChange:
                self._save_text_items_to_db()
            return QGraphicsTextItem.itemChange(item, change, value)

        return handler

    def _get_default_text_font(self):
        font = QFont()
        font.setPointSize(18)
        font.setFamily("Arial")
        return font

    def _save_text_items_to_db(self):
        # Save all text items to the database (via application_settings or similar)
        text_items_data = []
        for item in self._text_items:
            text_items_data.append(
                {
                    "text": item.toPlainText(),
                    "x": item.pos().x(),
                    "y": item.pos().y(),
                    "color": item.defaultTextColor().name(),
                    "font": item.font().toString(),
                }
            )
        # Store in application_settings (or replace with actual DB call)
        self.update_drawing_pad_settings(text_items=text_items_data)

    def update_drawing_pad_settings(self, **kwargs):
        for layer_item in self.layers:
            super().update_drawing_pad_settings(
                layer_id=layer_item.id, **kwargs
            )

    def _restore_text_items_from_db(self):
        # Restore text items from the database (via application_settings or similar)
        self._clear_text_items()
        text_items_data = getattr(self.drawing_pad_settings, "text_items", [])
        for data in text_items_data:
            text = data.get("text", "")
            x = data.get("x", 0)
            y = data.get("y", 0)
            color = QColor(data.get("color", "white"))
            font = QFont()
            font.fromString(data.get("font", ""))
            text_item = QGraphicsTextItem(text)
            text_item.setPos(QPointF(x, y))
            text_item.setDefaultTextColor(color)
            text_item.setFont(font)
            text_item.setFlag(QGraphicsTextItem.ItemIsMovable, True)
            text_item.setFlag(QGraphicsTextItem.ItemIsSelectable, True)
            text_item.setFlag(QGraphicsTextItem.ItemIsFocusable, True)
            text_item.setFlag(QGraphicsTextItem.ItemSendsGeometryChanges, True)
            text_item.setZValue(20)
            text_item.focusOutEvent = self._make_text_focus_out_handler(
                text_item
            )
            text_item.keyPressEvent = self._make_text_key_press_handler(
                text_item
            )
            text_item.itemChange = self._make_text_item_change_handler(
                text_item
            )
            self.scene.addItem(text_item)
            self._text_items.append(text_item)

    def _clear_text_items(self):
        for item in self._text_items:
            self.scene.removeItem(item)
        self._text_items.clear()

    def _set_text_items_interaction(self, enable: bool):
        # Enable/disable moving/editing for all text items
        for item in self._text_items:
            if enable:
                item.setFlag(QGraphicsTextItem.ItemIsMovable, True)
                item.setFlag(QGraphicsTextItem.ItemIsSelectable, True)
            else:
                item.setFlag(QGraphicsTextItem.ItemIsMovable, False)
                item.setFlag(QGraphicsTextItem.ItemIsSelectable, False)
                item.setTextInteractionFlags(Qt.NoTextInteraction)
