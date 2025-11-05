"""Mixin for zoom handling in CustomGraphicsView.

This mixin handles mouse wheel zoom and zoom level change signals.
"""


class ZoomMixin:
    """Provides zoom management for graphics view.

    This mixin manages:
    - Mouse wheel zoom events
    - Zoom level change signal handling
    - Transform updates based on zoom

    Dependencies:
        - self.zoom_handler: ZoomHandler instance
        - self.setTransform(): Qt method to set view transform
        - self.do_draw(): Redraw method
    """

    def on_zoom_level_changed_signal(self):
        """Handle zoom level change signal.

        Updates the view transform based on the new zoom level and redraws.
        """
        transform = self.zoom_handler.on_zoom_level_changed()

        # Set the transform
        self.setTransform(transform)

        # Redraw lines
        self.do_draw()

    def wheelEvent(self, event):
        """Handle mouse wheel events for zooming.

        Args:
            event: Qt wheel event containing delta and position.
        """
        transform = self.zoom_handler.wheelEvent(event)

        # Set the new transform
        self.setTransform(transform)

        # Redraw grid lines
        self.do_draw()
