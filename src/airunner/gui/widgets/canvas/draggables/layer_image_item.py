from typing import Optional, Dict
from PySide6.QtWidgets import QGraphicsItem
from PySide6.QtCore import Qt, QPointF
from airunner.enums import SignalCode, CanvasToolName
from airunner.utils.application.snap_to_grid import snap_to_grid
from airunner.gui.widgets.canvas.draggables.draggable_pixmap import (
    DraggablePixmap,
)


class LayerImageItem(DraggablePixmap):
    def __init__(self, pixmap, layer_image_data: Optional[Dict] = None):
        self.layer_image_data = layer_image_data or {}
        super().__init__(pixmap)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)

        # Add tracking variables for dragging, just like ActiveGridArea
        self.initial_mouse_scene_pos = None
        self.initial_item_abs_pos = None
        self.mouse_press_pos = None
        self._current_snapped_pos = (0, 0)

    def update_position(
        self,
        x: Optional[int] = None,
        y: Optional[int] = None,
        save: bool = True,
    ):
        super().update_position(x, y, save)

        if save:
            self.update_drawing_pad_settings("x_pos", x)
            self.update_drawing_pad_settings("y_pos", y)

    def mousePressEvent(self, event):
        # Handle drag initiation similar to ActiveGridArea
        if event.button() == Qt.MouseButton.LeftButton:
            # Store the initial scene position of the mouse
            self.initial_mouse_scene_pos = event.scenePos()

            # Store current absolute position
            abs_x = self.drawing_pad_settings.x_pos
            abs_y = self.drawing_pad_settings.y_pos
            if abs_x is None:
                abs_x = 0
            if abs_y is None:
                abs_y = 0
            self.initial_item_abs_pos = QPointF(abs_x, abs_y)

            # Store item-relative position for release check
            self.mouse_press_pos = event.pos()
            event.accept()
        else:
            # Not dragging this item, let base class handle
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        # Only do the complex drag calculations if we're actually dragging
        if self.initial_mouse_scene_pos is not None:
            # Calculate delta from initial press in scene coordinates
            delta = event.scenePos() - self.initial_mouse_scene_pos

            # Calculate new proposed absolute position
            proposed_abs_x = self.initial_item_abs_pos.x() + delta.x()
            proposed_abs_y = self.initial_item_abs_pos.y() + delta.y()

            # Apply grid snapping if enabled
            if self.grid_settings.snap_to_grid:
                snapped_abs_x, snapped_abs_y = snap_to_grid(
                    self.grid_settings, proposed_abs_x, proposed_abs_y
                )
            else:
                snapped_abs_x, snapped_abs_y = proposed_abs_x, proposed_abs_y

            # Get canvas offset just like ActiveGridArea
            try:
                view = self.scene().views()[0]
                canvas_offset = view.canvas_offset
            except (AttributeError, IndexError):
                canvas_offset = QPointF(0, 0)

            # Set visual position directly for smooth performance
            display_x = snapped_abs_x - canvas_offset.x()
            display_y = snapped_abs_y - canvas_offset.y()
            self.setPos(display_x, display_y)

            # Store current snapped position for release handler to use
            self._current_snapped_pos = (
                int(snapped_abs_x),
                int(snapped_abs_y),
            )

            # Accept the event to prevent further processing
            event.accept()
        else:
            # Fast path for non-drag mouse moves - just call superclass
            # and don't do any unnecessary calculations
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self.initial_mouse_scene_pos is not None:
            # Check if the item has actually moved
            has_moved = False
            if self.mouse_press_pos:
                has_moved = (
                    self.mouse_press_pos.x() != event.pos().x()
                    or self.mouse_press_pos.y() != event.pos().y()
                )

            # Reset drag tracking
            self.initial_mouse_scene_pos = None
            self.initial_item_abs_pos = None
            self.mouse_press_pos = None

            # Save the new position if moved
            if has_moved:
                # Save the snapped absolute position
                if (
                    int(self._current_snapped_pos[0])
                    != self.drawing_pad_settings.x_pos
                    or int(self._current_snapped_pos[1])
                    != self.drawing_pad_settings.y_pos
                ):
                    # Update settings with new position
                    self.update_drawing_pad_settings(
                        "x_pos", int(self._current_snapped_pos[0])
                    )
                    self.update_drawing_pad_settings(
                        "y_pos", int(self._current_snapped_pos[1])
                    )

                    # Update layer image data
                    self.layer_image_data["pos_x"] = int(
                        self._current_snapped_pos[0]
                    )
                    self.layer_image_data["pos_y"] = int(
                        self._current_snapped_pos[1]
                    )

                    # Critical fix: Update scene's position tracking
                    try:
                        scene = self.scene()
                        if scene and hasattr(
                            scene, "_original_item_positions"
                        ):
                            # Update the scene's tracked position for this item
                            scene._original_item_positions[self] = QPointF(
                                int(self._current_snapped_pos[0]),
                                int(self._current_snapped_pos[1]),
                            )
                    except (AttributeError, IndexError):
                        pass

                    # Signal image updated
                    self.api.art.canvas.image_updated()

            # Accept the event
            event.accept()
        else:
            # Let the base class handle it
            super().mouseReleaseEvent(event)
