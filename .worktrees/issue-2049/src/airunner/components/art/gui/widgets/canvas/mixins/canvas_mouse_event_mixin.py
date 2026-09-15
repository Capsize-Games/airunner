"""Mixin for handling mouse and wheel events on the canvas."""

from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QGraphicsSceneMouseEvent


class CanvasMouseEventMixin:
    """Handles mouse and wheel events for canvas interaction.

    This mixin provides mouse event handling for panning, zooming, drawing,
    and cursor management.
    """

    def wheelEvent(self, event: Any) -> None:
        """Handle mouse wheel events for zooming.

        Args:
            event: The wheel event containing delta and modifiers.
        """
        if not hasattr(event, "delta"):
            return

        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            zoom_in_factor = self.grid_settings.zoom_in_step
            zoom_out_factor = -self.grid_settings.zoom_out_step

            if event.delta() > 0:
                zoom_factor = zoom_in_factor
            else:
                zoom_factor = zoom_out_factor

            zoom_level = self.grid_settings.zoom_level
            zoom_level += zoom_factor
            if zoom_level < 0.1:
                zoom_level = 0.1
            self.update_grid_settings(zoom_level=zoom_level)
            self.api.art.canvas.zoom_level_changed()

    def mousePressEvent(self, event: Any) -> None:
        """Handle mouse press events.

        Args:
            event: The mouse press event.
        """
        if isinstance(event, QGraphicsSceneMouseEvent):
            if event.button() == Qt.MouseButton.RightButton:
                self.right_mouse_button_pressed = True
                self.start_pos = event.scenePos()
            elif event.button() == Qt.MouseButton.LeftButton:
                super(CanvasMouseEventMixin, self).mousePressEvent(event)
        self._handle_cursor(event)
        self.last_pos = event.scenePos()
        self.update()

        if event.button() == Qt.MouseButton.LeftButton:
            self._handle_left_mouse_press(event)
            self._handle_cursor(event)
            if not self.is_brush_or_eraser:
                super().mousePressEvent(event)
            elif self.drawing_pad_settings.enable_automatic_drawing:
                self.api.art.canvas.interrupt_image_generation()

    def mouseReleaseEvent(self, event: Any) -> None:
        """Handle mouse release events.

        Args:
            event: The mouse release event.
        """
        if event.button() == Qt.MouseButton.RightButton:
            self.right_mouse_button_pressed = False
        else:
            self._handle_left_mouse_release(event)
            super(CanvasMouseEventMixin, self).mouseReleaseEvent(event)
        super().mouseReleaseEvent(event)
        self._handle_cursor(event)
        if event.button() == Qt.MouseButton.LeftButton:
            self.last_pos = None
            self.start_pos = None
            self.do_update = False
            if self.drawing_pad_settings.enable_automatic_drawing:
                if self._is_drawing or self._is_erasing:
                    self.api.art.generate_image()
            self._is_drawing = False
            self._is_erasing = False

    def mouseMoveEvent(self, event: Any) -> None:
        """Handle mouse move events for panning and drawing.

        Args:
            event: The mouse move event.
        """
        if self.right_mouse_button_pressed:
            view = self.views()[0]
            view.setTransformationAnchor(view.ViewportAnchor.NoAnchor)
            view.setResizeAnchor(view.ViewportAnchor.NoAnchor)
            delta = event.scenePos() - self.last_pos
            scale_factor = view.transform().m11()
            view.translate(delta.x() / scale_factor, delta.y() / scale_factor)
            self.last_pos = event.scenePos()
        else:
            super(CanvasMouseEventMixin, self).mouseMoveEvent(event)

        self.last_pos = event.scenePos()
        self.update()

    def enterEvent(self, event: Any) -> None:
        """Handle mouse enter events.

        Args:
            event: The enter event.
        """
        self._handle_cursor(event, True)

    def leaveEvent(self, event: Any) -> None:
        """Handle mouse leave events.

        Args:
            event: The leave event.
        """
        self._handle_cursor(event, False)

    def _handle_left_mouse_press(self, event: Any) -> None:
        """Handle left mouse button press internal logic.

        Args:
            event: The mouse press event.
        """
        try:
            self.start_pos = event.scenePos()
        except AttributeError:
            pass
        # Mark that user is interacting (drawing)
        self._persist_timer.stop()
        self._is_user_interacting = True

    def _handle_left_mouse_release(self, event: Any) -> None:
        """Handle left mouse button release internal logic.

        Args:
            event: The mouse release event.
        """
        # Stroke finished; allow persistence after a short grace period
        self._is_user_interacting = False
        if (
            self._pending_image_ref is not None
            or self._pending_image_binary is not None
        ):
            self._persist_timer.start(self._persist_delay_ms)
