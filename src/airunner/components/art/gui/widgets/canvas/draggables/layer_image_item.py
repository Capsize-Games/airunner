from typing import Optional, Dict
from PySide6.QtWidgets import QGraphicsItem
from PySide6.QtCore import QPointF
from airunner.enums import CanvasToolName
from airunner.components.art.utils.canvas_position_manager import (
    CanvasPositionManager,
    ViewState,
)
from airunner.components.art.gui.widgets.canvas.draggables.draggable_pixmap import (
    DraggablePixmap,
)


class LayerImageItem(DraggablePixmap):
    def __init__(
        self,
        qimage,
        *,
        layer_id: Optional[int] = None,
        layer_image_data: Optional[Dict] = None,
        use_layer_context: bool = True,
    ):
        self._layer_id: Optional[int] = layer_id
        self.layer_image_data = layer_image_data or {}
        super().__init__(qimage, layer_id=layer_id, use_layer_context=use_layer_context)
        self.set_layer_context(layer_id)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)

        # Add tracking variables for dragging, just like ActiveGridArea
        self.initial_mouse_scene_pos = None
        self.initial_item_abs_pos = None
        self.mouse_press_pos = None
        self._current_snapped_pos = (0, 0)

    @property
    def layer_id(self) -> Optional[int]:
        return self._layer_id

    @layer_id.setter
    def layer_id(self, value: Optional[int]) -> None:
        self._layer_id = value
        self.set_layer_context(value)

    def update_position(
        self,
        x: Optional[int] = None,
        y: Optional[int] = None,
        save: bool = True,
    ):
        super().update_position(x, y, save)

        if save and x is not None and y is not None:
            # Convert display position to absolute position by adding canvas offset
            try:
                view = self.scene().views()[0]
                canvas_offset = view.canvas_offset
                abs_x = x + canvas_offset.x()
                abs_y = y + canvas_offset.y()

                self.logger.warning(
                    f"[SAVE LAYER] Layer {self.layer_id}: saving absolute pos x={abs_x}, y={abs_y} (display_pos={x}, {y}, canvas_offset=({canvas_offset.x()}, {canvas_offset.y()}))"
                )

                self.update_drawing_pad_settings(
                    x_pos=int(abs_x), y_pos=int(abs_y), layer_id=self.layer_id
                )
            except (AttributeError, IndexError):
                # Fallback if we can't get canvas_offset - just save display position
                self.update_drawing_pad_settings(
                    x_pos=x, y_pos=y, layer_id=self.layer_id
                )

    def mousePressEvent(self, event):
        if self.current_tool not in [CanvasToolName.MOVE]:
            super().mousePressEvent(event)
            return

        view = self.scene().views()[0]

        if hasattr(self.scene(), "is_dragging"):
            self.scene().is_dragging = True

        # Create ViewState from view
        view_state = ViewState(
            canvas_offset=QPointF(
                getattr(view, "canvas_offset_x", 0.0),
                getattr(view, "canvas_offset_y", 0.0),
            ),
            grid_compensation=getattr(view, "grid_compensation_offset", QPointF(0.0, 0.0)),
        )

        # Use manager to convert display position to absolute position
        manager = CanvasPositionManager()
        self.drag_start_abs_pos = manager.display_to_absolute(
            self.pos(), view_state
        )
        self.drag_start_mouse_pos = event.scenePos()

        event.accept()

    def mouseMoveEvent(self, event):
        if self.current_tool not in [CanvasToolName.MOVE]:
            super().mouseMoveEvent(event)
            return

        view = self.scene().views()[0]

        # Create ViewState from view
        view_state = ViewState(
            canvas_offset=QPointF(
                getattr(view, "canvas_offset_x", 0.0),
                getattr(view, "canvas_offset_y", 0.0),
            ),
            grid_compensation=getattr(view, "grid_compensation_offset", QPointF(0.0, 0.0)),
        )

        # Use manager to calculate drag position
        manager = CanvasPositionManager()
        mouse_delta = event.scenePos() - self.drag_start_mouse_pos

        # Enable snap-to-grid during drag if enabled
        snap_enabled = self.grid_settings.snap_to_grid
        cell_size = self.grid_settings.cell_size if snap_enabled else 0
        center_pos = getattr(view, "center_pos", QPointF(0, 0))

        _, new_display_pos = manager.calculate_drag_position(
            self.drag_start_abs_pos,
            mouse_delta,
            view_state,
            snap_enabled=snap_enabled,
            cell_size=cell_size,
            grid_origin=center_pos,
        )

        self.setPos(new_display_pos)
        event.accept()

    def mouseReleaseEvent(self, event):
        if self.current_tool not in [CanvasToolName.MOVE]:
            super().mouseReleaseEvent(event)
            return

        view = self.scene().views()[0]

        # Create ViewState from view
        view_state = ViewState(
            canvas_offset=QPointF(
                getattr(view, "canvas_offset_x", 0.0),
                getattr(view, "canvas_offset_y", 0.0),
            ),
            grid_compensation=getattr(view, "grid_compensation_offset", QPointF(0.0, 0.0)),
        )

        manager = CanvasPositionManager()

        # Convert current display position to absolute position
        abs_pos = manager.display_to_absolute(self.pos(), view_state)

        # Snap to grid in absolute space if enabled
        if self.grid_settings.snap_to_grid:
            center_pos = getattr(view, "center_pos", QPointF(0, 0))
            abs_pos = manager.snap_to_grid(
                abs_pos, self.grid_settings.cell_size, grid_origin=center_pos
            )

            # Update display position to snapped absolute position
            display_pos = manager.absolute_to_display(abs_pos, view_state)
            self.setPos(display_pos)

        # Save the absolute position to database
        self.save_position(abs_pos)

        event.accept()

        # Clear drag flag after a longer delay to ensure ALL signal processing completes
        # Database updates can trigger multiple cascading signals
        from PySide6.QtCore import QTimer

        QTimer.singleShot(
            500,  # Increased to 500ms to ensure signals are fully processed
            lambda: (
                setattr(self.scene(), "is_dragging", False)
                if hasattr(self.scene(), "is_dragging")
                else None
            ),
        )

    def save_position(self, abs_pos: QPointF):
        """Save the absolute position to database."""
        # Only save if position changed
        if (
            int(abs_pos.x()) != self.drawing_pad_settings.x_pos
            or int(abs_pos.y()) != self.drawing_pad_settings.y_pos
        ):
            # Update settings with new position
            self.update_drawing_pad_settings(
                x_pos=int(abs_pos.x()),
                y_pos=int(abs_pos.y()),
                layer_id=self.layer_id,
            )

            # Update layer image data
            self.layer_image_data["pos_x"] = int(abs_pos.x())
            self.layer_image_data["pos_y"] = int(abs_pos.y())

            # Update scene's position tracking
            try:
                scene = self.scene()
                if scene and hasattr(scene, "original_item_positions"):
                    scene.original_item_positions[self] = abs_pos
            except (AttributeError, IndexError):
                pass

            # NOTE: Don't call image_updated() here as it triggers
            # a full refresh that repositions everything, causing snap-back
            # self.api.art.canvas.image_updated()

            # Commit history transaction
            try:
                scene = self.scene()
                if scene and hasattr(
                    scene, "_commit_layer_history_transaction"
                ):
                    scene._commit_layer_history_transaction(
                        self.layer_id, "position"
                    )
            except Exception:
                pass
        else:
            # Cancel history transaction if no change
            try:
                scene = self.scene()
                if scene and hasattr(
                    scene, "_cancel_layer_history_transaction"
                ):
                    scene._cancel_layer_history_transaction(self.layer_id)
            except Exception:
                pass
