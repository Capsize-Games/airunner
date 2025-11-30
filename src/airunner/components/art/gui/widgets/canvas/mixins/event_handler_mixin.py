"""Event handler mixin for CustomGraphicsView.

This mixin handles Qt event processing including mouse, keyboard, wheel,
resize, and show events for the canvas view.
"""

from PySide6.QtCore import QEvent, QPointF, Qt, QTimer
from PySide6.QtGui import QMouseEvent, QResizeEvent



class EventHandlerMixin:
    """Mixin for Qt event handling in CustomGraphicsView.

    This mixin handles:
    - Mouse events (press, release, move) for panning
    - Keyboard events (delete key for text items)
    - Wheel events (zoom with Ctrl modifier)
    - Resize events with viewport compensation
    - Show events for initialization
    - Enter/leave events for cursor management
    - Pan update timer for smooth panning

    Attributes:
        _middle_mouse_pressed: Flag indicating middle mouse button state
        last_pos: Last mouse position during pan
        _pan_update_timer: Timer for batching pan updates
        _pending_pan_event: Flag for pending pan update
    """

    def wheelEvent(self, event) -> None:
        """Handle mouse wheel events for zooming.

        Only allows zooming when Ctrl modifier is pressed to avoid
        accidental scrolling.

        Args:
            event: Qt wheel event.
        """
        # Only allow zooming with Ctrl, otherwise ignore scrolling
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            super().wheelEvent(event)
            self.draw_grid()  # Only redraw grid on zoom
        else:
            event.ignore()  # Prevent QGraphicsView from scrolling

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """Handle mouse press events.

        Handles middle mouse button for panning.
        Args:
            event: Qt mouse event.
        """
        if event.button() == Qt.MouseButton.MiddleButton:
            self._middle_mouse_pressed = True
            self.last_pos = event.pos()
            event.accept()
            return

        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        """Handle mouse release events.

        Handles middle mouse button release and saves canvas offset.

        Args:
            event: Qt mouse event.
        """
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

        # Delegate to other handlers
        super().mouseReleaseEvent(event)

    def mouseMoveEvent(self, event) -> None:
        """Handle mouse move events for panning and text dragging.

        Implements smooth panning with middle mouse button using a timer
        to batch updates.

        Args:
            event: Qt mouse event.
        """
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

        # Delegate to other handlers (e.g., text dragging)
        super().mouseMoveEvent(event)

    def keyPressEvent(self, event) -> None:
        """Handle keyboard events.

        Supports:
        - Delete key for removing selected text items
        - Ctrl+C for copying image to clipboard
        - Ctrl+V for pasting image from clipboard
        - Ctrl+X for cutting image

        Args:
            event: Qt keyboard event.
        """
        # Handle Ctrl+C (copy)
        if event.key() == Qt.Key.Key_C and event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            self.api.art.canvas.copy_image()
            event.accept()
            return
        
        # Handle Ctrl+V (paste)
        if event.key() == Qt.Key.Key_V and event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            self.api.art.canvas.paste_image()
            event.accept()
            return
        
        # Handle Ctrl+X (cut)
        if event.key() == Qt.Key.Key_X and event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            self.api.art.canvas.cut_image()
            event.accept()
            return
        
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

    def _do_pan_update(self) -> None:
        """Execute pan update to refresh positions and grid.

        Called by timer to batch pan updates for smooth panning.
        """
        self.update_active_grid_area_position()
        self.updateImagePositions()
        self.draw_grid()
        if self._pending_pan_event:
            self._pending_pan_event = False
            self._pan_update_timer.start(1)

    def showEvent(self, event) -> None:
        """Handle show event for canvas initialization and restoration.

        On first show, loads saved offsets and initializes the canvas.
        On subsequent shows, handles viewport size changes that occurred
        while hidden.

        Args:
            event: Qt show event.
        """
        super().showEvent(event)

        # If this is the first time showing (initial load)
        if not self._initialized:
            # Set restoration flag to prevent resize compensation during initial load
            self._is_restoring_state = True

            # Reset grid compensation on load to prevent accumulated drift
            self._grid_compensation_offset = QPointF(0, 0)

            # Load offset first - this ONLY sets the canvas_offset to the saved value
            self.load_canvas_offset()

            # Store the loaded offset to restore it after any operations
            loaded_offset = QPointF(
                self.canvas_offset.x(), self.canvas_offset.y()
            )

            # Clear any cached positions since we're starting fresh
            if self.scene and hasattr(self.scene, "original_item_positions"):
                self.scene.original_item_positions.clear()

            # Set up the scene (grid, etc.) - DO NOT let these change the offset
            self.do_draw(True)
            self.toggle_drag_mode()
            self.set_canvas_color(self.scene)

            # Restore the offset after do_draw
            self.canvas_offset = loaded_offset

            # Show the active grid area using loaded offset (this also positions it)
            self.show_active_grid_area()

            # Restore the offset after show_active_grid_area
            self.canvas_offset = loaded_offset

            # Update viewport size tracking without adjusting offset
            self._last_viewport_size = self.viewport().size()

            # Ensure layers are created/initialized at their saved positions
            # This method loads positions from DB and applies them correctly
            if hasattr(self.scene, "_refresh_layer_display"):
                self.scene._refresh_layer_display()

            # FORCE the offset back to loaded value after layer initialization
            self.canvas_offset = loaded_offset

            # Final offset restoration
            self.canvas_offset = loaded_offset

            self._initialized = True

            # If canvas_offset is (0,0), the user had clicked "center" before closing.
            # We need to recenter for the current viewport, but viewport size may not be 
            # correct yet during showEvent. Store a flag and do it in the delayed callback.
            self._needs_recenter_on_show = (loaded_offset == QPointF(0, 0))
            
            if self._needs_recenter_on_show:
                self.logger.info(
                    "[SHOW] Canvas offset is (0,0) - will recenter after window settles"
                )
                # Clear cached positions so they get recalculated
                if self.scene and hasattr(self.scene, "original_item_positions"):
                    self.scene.original_item_positions = {}
            else:
                # Non-zero offset means user panned - restore exact positions
                self.align_canvas_items_to_viewport()

            # Use a longer delay to allow the window to fully settle (including main window showEvent)
            # before re-enabling resize compensation. The main window's showEvent can fire up to 1 second
            # after the canvas showEvent completes, causing resize events that shouldn't apply compensation.
            QTimer.singleShot(1500, self._finish_state_restoration)
        else:
            # Already initialized - this is a subsequent show (e.g., switching back to canvas tab)
            # Check if viewport size changed while we were hidden
            current_viewport_size = self.viewport().size()
            if current_viewport_size != self._last_viewport_size:
                self.logger.info(
                    f"[SHOW] Viewport size changed while hidden: {self._last_viewport_size} -> {current_viewport_size}"
                )

                # Calculate the shift that occurred while hidden
                old_center_x = self._last_viewport_size.width() / 2
                old_center_y = self._last_viewport_size.height() / 2
                new_center_x = current_viewport_size.width() / 2
                new_center_y = current_viewport_size.height() / 2

                center_shift_x = new_center_x - old_center_x
                center_shift_y = new_center_y - old_center_y

                # Apply the compensation for the resize that happened while hidden
                if not self._is_restoring_state:
                    self._apply_viewport_compensation(
                        center_shift_x, center_shift_y
                    )

                # Update tracked size
                self._last_viewport_size = current_viewport_size

                # Redraw grid
                self.draw_grid()

    def _finish_state_restoration(self) -> None:
        """Called after delay to finish state restoration and re-enable resize compensation."""
        self._is_restoring_state = False

        # Reload and reapply the canvas offset one final time to ensure it's correct
        x = self.settings.value("canvas_offset_x", 0.0)
        y = self.settings.value("canvas_offset_y", 0.0)
        final_offset = QPointF(float(x), float(y))
        self.canvas_offset = final_offset

        # Check if we need to recenter (user had clicked center before closing)
        if getattr(self, "_needs_recenter_on_show", False):
            self._needs_recenter_on_show = False
            self.logger.info(
                "[FINISH] Recentering for current viewport (delayed)"
            )
            
            # Now viewport should have correct size - recenter everything
            self.center_pos = QPointF(0, 0)
            
            # Calculate center_pos for current viewport
            pos_x, pos_y = self.get_recentered_position(
                self.application_settings.working_width,
                self.application_settings.working_height,
            )
            self.center_pos = QPointF(pos_x, pos_y)
            self.logger.info(
                f"[FINISH] Calculated center_pos: x={pos_x}, y={pos_y}"
            )
            
            # Update active grid settings and position
            self.update_active_grid_settings(pos_x=pos_x, pos_y=pos_y)
            self.update_active_grid_area_position()
            
            # Recenter layer positions for the current viewport and apply them
            layer_positions = self.recenter_layer_positions()
            self.updateImagePositions(layer_positions)
            # Store the new positions so future updates use the correct values
            if self.scene:
                self.scene.original_item_positions.update(layer_positions)
        else:
            # Normal restoration - update positions from saved values
            self.update_active_grid_area_position()
            self.updateImagePositions()

        self.logger.debug(
            f"Canvas state restoration complete - final offset: ({final_offset.x()}, {final_offset.y()})"
        )
        self.scene.show_event()

    def resizeEvent(self, event: "QResizeEvent") -> None:
        """Handle viewport resize to keep canvas centered without changing offset values.

        When the viewport resizes, the visual center shifts but the canvas offset
        (which represents the user's pan position) should remain unchanged. We compensate
        by adjusting the stored absolute positions of items to account for the viewport
        center change.

        Args:
            event: Qt resize event.
        """
        super().resizeEvent(event)

        # Skip compensation during initial state restoration
        if self._is_restoring_state or not self._initialized:
            self.logger.info(
                f"[RESIZE] Skipping compensation - _is_restoring_state={self._is_restoring_state}, _initialized={self._initialized}"
            )
            self._last_viewport_size = self.viewport().size()
            return

        self.logger.info(
            f"[RESIZE] Processing resize - old_size={self._last_viewport_size}, new_size={self.viewport().size()}"
        )

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

    def enterEvent(self, event: QEvent) -> None:
        """Handle event when mouse enters the widget.

        Delegates cursor handling to the scene.

        Args:
            event: Qt event.
        """
        self.scene.enterEvent(event)
        super().enterEvent(event)

    def leaveEvent(self, event: QEvent) -> None:
        """Handle event when mouse leaves the widget.

        Resets cursor to normal pointer.

        Args:
            event: Qt event.
        """
        self.scene.leaveEvent(event)
        super().leaveEvent(event)
