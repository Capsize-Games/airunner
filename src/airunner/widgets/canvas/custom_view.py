from typing import Optional, Dict

from PySide6 import QtGui
from PySide6.QtCore import QPointF, QPoint, Qt, QRect, QEvent
from PySide6.QtGui import QMouseEvent, QColor, QBrush, QPen
from PySide6.QtWidgets import (
    QGraphicsView, 
    QGraphicsItemGroup, 
    QGraphicsLineItem, 
    QGraphicsScene
)

from airunner.enums import CanvasToolName, SignalCode, CanvasType
from airunner.mediator_mixin import MediatorMixin
from airunner.utils.image import convert_image_to_binary
from airunner.utils import snap_to_grid
from airunner.widgets.canvas.brush_scene import BrushScene
from airunner.widgets.canvas.custom_scene import CustomScene
from airunner.widgets.canvas.draggables.active_grid_area import ActiveGridArea
from airunner.windows.main.settings_mixin import SettingsMixin
from airunner.widgets.canvas.zoom_handler import ZoomHandler
from airunner.utils.settings import get_qsettings


class CustomGraphicsView(
    MediatorMixin,
    SettingsMixin,
    QGraphicsView,
):
    def __init__(self, *args, **kwargs):
        super().__init__()
        self.setMouseTracking(True)
        
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
        self.last_pos: QPoint = QPoint(0, 0)
        self.zoom_handler: ZoomHandler = ZoomHandler()
        self.canvas_offset = QPoint(0, 0)  # Offset for infinite scrolling
        self.settings = get_qsettings()
        self._middle_mouse_pressed: bool = False
        self.load_canvas_offset()

        # Add settings to handle negative coordinates properly
        self.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.FullViewportUpdate)
        
        # Use setOptimizationFlags directly instead of the enum that doesn't exist in your PySide6 version
        self.setOptimizationFlags(QGraphicsView.OptimizationFlag.DontAdjustForAntialiasing | 
                                 QGraphicsView.OptimizationFlag.DontSavePainterState)

        # register signal handlers
        signal_handlers = {
            SignalCode.APPLICATION_TOOL_CHANGED_SIGNAL: self.on_tool_changed_signal,
            SignalCode.CANVAS_ZOOM_LEVEL_CHANGED: self.on_zoom_level_changed_signal,
            SignalCode.SET_CANVAS_COLOR_SIGNAL: self.set_canvas_color,
            SignalCode.CANVAS_DO_DRAW_SELECTION_AREA_SIGNAL: self.draw_selected_area,
            SignalCode.UPDATE_SCENE_SIGNAL: self.update_scene,
            SignalCode.CANVAS_CLEAR_LINES_SIGNAL: self.clear_lines,
            SignalCode.SCENE_DO_DRAW_SIGNAL: self.on_canvas_do_draw_signal,
            SignalCode.APPLICATION_MAIN_WINDOW_LOADED_SIGNAL: self.on_main_window_loaded_signal,
            SignalCode.APPLICATION_SETTINGS_CHANGED_SIGNAL: self.on_application_settings_changed_signal,
            SignalCode.ACTIVE_GRID_AREA_MOVED_SIGNAL: self.handle_active_grid_area_moved_signal,
            SignalCode.MASK_GENERATOR_WORKER_RESPONSE_SIGNAL: self.on_mask_generator_worker_response_signal,
            SignalCode.RECENTER_GRID_SIGNAL: self.on_recenter_grid_signal,
        }
        for k, v in signal_handlers.items():
            self.register(k, v)

    def load_canvas_offset(self):
        """Load the canvas offset from QSettings."""
        x = self.settings.value("canvas_offset_x", 0, type=float)
        y = self.settings.value("canvas_offset_y", 0, type=float)
        self.canvas_offset = QPointF(x, y)

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
                import traceback
                traceback.print_stack()
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
        return CanvasToolName(self.application_settings.current_tool)

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

    def handle_active_grid_area_moved_signal(self):
        self.active_grid_area.snap_to_grid()

    def on_recenter_grid_signal(self):
        self.canvas_offset = QPoint(0, 0)
        self.do_draw()

    def on_mask_generator_worker_response_signal(self, message: dict):
        mask = message["mask"]
        if mask is not None:
            mask = convert_image_to_binary(mask)
            self.update_drawing_pad_settings("mask", mask)

    def on_main_window_loaded_signal(self):
        self.initialized = True
        self.do_draw()

    def on_canvas_do_draw_signal(self, data: dict):
        self.do_draw(force_draw=data.get("force_draw", False))

    def on_application_settings_changed_signal(self, data: Dict):
        if (
            data.get("setting_name") == "grid_settings" and 
            data.get("column_name") == "canvas_color" and 
            self._canvas_color != data.get("value", self._canvas_color) and
            self.scene
        ):
            self._canvas_color = data.get("value")
            self.set_canvas_color(self.scene, self._canvas_color)

        if self.grid_settings.show_grid:
            self.do_draw()
        else:
            self.clear_lines()

    def do_draw(
        self,
        force_draw: bool = False
    ):
        if (self.drawing or not self.initialized) and not force_draw:
            return
        self.drawing = True
        self.set_scene_rect()
        if self.grid_settings.show_grid:
            self.draw_grid()
        else:
            self.clear_lines()
        self.show_active_grid_area()
        self.update_scene()
        self.drawing = False

    def draw_grid(self):
        if not self.__can_draw_grid:
            return

        if self.line_group is None:
            self.line_group = QGraphicsItemGroup()

        if self.line_group.scene() != self.scene:
            self.scene.addItem(self.line_group)

        cell_size = self.grid_settings.cell_size
        scene_width = int(self.scene.width())
        scene_height = int(self.scene.height())

        # Adjust for canvas offset
        offset_x = self.canvas_offset.x() % cell_size
        offset_y = self.canvas_offset.y() % cell_size

        num_vertical_lines = scene_width // cell_size + 2
        num_horizontal_lines = scene_height // cell_size + 2

        color = QColor(self.grid_settings.line_color)
        pen = QPen(
            color,
            self.grid_settings.line_width,
        )

        # Create or reuse vertical lines
        for i in range(num_vertical_lines):
            x = i * cell_size - offset_x
            if i < len(self.line_group.childItems()):
                line = self.line_group.childItems()[i]
                line.setLine(x, 0, x, scene_height)
                line.setVisible(True)
                line.setPen(pen)
            else:
                line = QGraphicsLineItem(x, 0, x, scene_height)
                self.line_group.addToGroup(line)

        # Create or reuse horizontal lines
        for i in range(num_horizontal_lines):
            y = i * cell_size - offset_y
            index = i + num_vertical_lines
            if index < len(self.line_group.childItems()):
                line = self.line_group.childItems()[index]
                line.setLine(0, y, scene_width, y)
                line.setVisible(True)
                line.setPen(pen)
            else:
                line = QGraphicsLineItem(0, y, scene_width, y)
                self.line_group.addToGroup(line)

        # Hide unused lines
        for i in range(num_vertical_lines + num_horizontal_lines, len(self.line_group.childItems())):
            self.line_group.childItems()[i].setVisible(False)

    def clear_lines(self):
        self.remove_scene_item(self.line_group)

    def register_line_data(self, lines_data):
        for line_data in lines_data:
            try:
                line = self.scene.addLine(*line_data)
                self.line_group.addToGroup(line)
            except TypeError as e:
                self.logger.error(f"TypeError: {e}")
            except AttributeError as e:
                self.logger.error(f"AttributeError: {e}")

    def set_scene_rect(self):
        if not self.scene:
            return
        canvas_container_size = self.viewport().size()
        self.scene.setSceneRect(
            0,
            0,
            canvas_container_size.width(),
            canvas_container_size.height()
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

    def draw_selected_area(self):
        """
        Draw the selected active grid area container
        """
        # Handle any active selections
        selection_start_pos = self.scene.selection_start_pos
        selection_stop_pos = self.scene.selection_stop_pos

        # This will clear the active grid area while a selection is being made
        if selection_stop_pos is None and selection_start_pos is not None:
            if self.active_grid_area:
                self.remove_scene_item(self.active_grid_area)
                self.active_grid_area = None
            return

        # this will update the active grid area in the settings
        if selection_start_pos is not None and selection_stop_pos is not None:
            rect = QRect(
                selection_start_pos,
                selection_stop_pos
            )

            # Ensure width and height ar divisible by 8
            width = rect.width()
            height = rect.height()
            if width % 8 != 0:
                width -= width % 8
            if height % 8 != 0:
                height -= height % 8

            cell_size = self.grid_settings.cell_size
            if width < cell_size:
                width = cell_size
            if height < cell_size:
                height = cell_size

            # Apply canvas offset to the position to maintain relative positioning
            x = rect.x() + self.canvas_offset.x()
            y = rect.y() + self.canvas_offset.y()

            self.update_active_grid_settings("pos_x", x)
            self.update_active_grid_settings("pos_y", y)
            self.update_generator_settings("width", width)
            self.update_generator_settings("height", height)
            self.update_application_settings("working_width", width)
            self.update_application_settings("working_height", height)

            # Clear the selection from the scene
            self.scene.clear_selection()
        self.show_active_grid_area()
        self.emit_signal(SignalCode.APPLICATION_ACTIVE_GRID_AREA_UPDATED)

    def show_active_grid_area(self):
        if not self.__do_show_active_grid_area:
            return

        # Create an ActiveGridArea object if it doesn't exist
        # and add it to the scene
        if not self.active_grid_area:
            self.active_grid_area = ActiveGridArea()
            self.active_grid_area.setZValue(10)
            self.scene.addItem(self.active_grid_area)
            
        # Adjust active grid area position based on canvas offset
        if self.active_grid_area:
            # Get the position from settings, subtract the canvas offset to display correctly
            pos_x = self.active_grid_settings.pos_x - self.canvas_offset.x()
            pos_y = self.active_grid_settings.pos_y - self.canvas_offset.y()
            
            # Update the position property of the active grid area
            self.active_grid_area.setPos(pos_x, pos_y)

    def on_zoom_level_changed_signal(self):
        transform = self.zoom_handler.on_zoom_level_changed()

        # Set the transform
        self.setTransform(transform)

        # Redraw lines
        self.do_draw()

    def resizeEvent(self, event: QtGui.QResizeEvent) -> None:
        super().resizeEvent(event)
        self.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.setSceneRect(0, 0, self.viewport().width(), self.viewport().height())
        self.do_draw()

    def showEvent(self, event):
        super().showEvent(event)

        self.setContentsMargins(0, 0, 0, 0)

        self.do_draw(True)

        self.scene.initialize_image()

        self.toggle_drag_mode()

        # Ensure the viewport is aligned to the top-left corner
        self.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.setSceneRect(0, 0, self.viewport().width(), self.viewport().height())
        self.set_canvas_color(self.scene)
        self.show_active_grid_area()

    def set_canvas_color(
        self, 
        scene: Optional[CustomScene] = None,
        canvas_color: Optional[str] = None
    ):
        scene = self.scene if not scene else scene
        canvas_color = canvas_color or self.grid_settings.canvas_color
        self.current_background_color = canvas_color
        color = QColor(self.current_background_color)
        brush = QBrush(color)
        scene.setBackgroundBrush(brush)

    def on_tool_changed_signal(self, message):
        self.toggle_drag_mode()

    def toggle_drag_mode(self):
        if self.current_tool is CanvasToolName.SELECTION:
            self.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
        else:
            self.setDragMode(QGraphicsView.DragMode.NoDrag)

    def snap_to_grid(self, event: QMouseEvent, use_floor: bool = True) -> QMouseEvent:
        """
        This is used to adjust the selection tool to the grid
        in real time during rubberband mode.
        :param event:
        :param use_floor:
        :return:
        """
        if self.current_tool is CanvasToolName.SELECTION:
            x, y = snap_to_grid(self.grid_settings, event.pos().x(), event.pos().y(), use_floor)
        else:
            x = event.pos().x()
            y = event.pos().y()

        x = float(x)
        y = float(y)

        point = QPointF(x, y)
        event_type: QEvent.Type = QEvent.Type(event.type())

        new_event = QMouseEvent(
            event_type,
            point,
            event.button(),
            event.buttons(),
            event.modifiers()
        )
        return new_event

    def mouseMoveEvent(self, event: QMouseEvent):
        if self._middle_mouse_pressed:
            delta = event.pos() - self.last_pos
            self.canvas_offset += delta
            self.last_pos = event.pos()
            
            # Update the active grid area position when panning
            if self.active_grid_area:
                pos_x = self.active_grid_settings.pos_x - self.canvas_offset.x()
                pos_y = self.active_grid_settings.pos_y - self.canvas_offset.y()
                self.active_grid_area.setPos(pos_x, pos_y)
            
            # Update image positions directly without relying on complex logic
            self.updateImagePositions()
            
            # Then update the grid
            self.do_draw()
                
        super().mouseMoveEvent(event)
    
    def updateImagePositions(self):
        """Update positions of all images in the scene based on canvas offset."""
        if not self.scene or not hasattr(self.scene, 'item') or not self.scene.item:
            return
        
        # Get the main item directly
        item = self.scene.item
        
        # Make sure the item is visible
        item.setVisible(True)
        
        # Store original position if needed
        if item not in self.scene._original_item_positions:
            self.scene._original_item_positions[item] = item.pos()
        
        # Get original position
        original_pos = self.scene._original_item_positions[item]
        
        # Calculate new position
        new_x = original_pos.x() - self.canvas_offset.x()
        new_y = original_pos.y() - self.canvas_offset.y()
        
        # Set new position
        item.setPos(new_x, new_y)
        
        # Ensure image has high Z value for visibility
        item.setZValue(5)
        
        # Ensure the item's bounding rect is properly updated
        item.prepareGeometryChange()
        
        # Force the scene to update the entire viewport
        self.scene.invalidate(item.boundingRect(), QGraphicsScene.SceneLayer.ItemLayer)
        
        # Force entire viewport update to handle negative coordinates
        self.viewport().update()

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.MiddleButton:
            self._middle_mouse_pressed = True
            self.last_pos = event.pos()

        new_event = self.snap_to_grid(event)

        super().mousePressEvent(new_event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.MiddleButton:
            self._middle_mouse_pressed = False
            self.last_pos = None
        super().mouseReleaseEvent(event)

    def leaveEvent(self, event: QEvent) -> None:
        """
        Handle the event when the mouse leaves the CustomGraphicsView widget.
        Resets the cursor to a normal pointer.
        """
        self.scene.leaveEvent(event)
        super().leaveEvent(event)

    def closeEvent(self, event):
        """Save canvas offset on close."""
        self.save_canvas_offset()
        super().closeEvent(event)
