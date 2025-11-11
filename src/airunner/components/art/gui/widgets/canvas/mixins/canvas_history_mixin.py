"""Canvas history and undo/redo mixin."""

from typing import Dict, Any, Optional
from dataclasses import asdict, is_dataclass
from PySide6.QtCore import QPointF, QTimer
from PIL import ImageQt

from airunner.components.art.data.drawingpad_settings import DrawingPadSettings
from airunner.components.art.utils.canvas_position_manager import (
    CanvasPositionManager,
    ViewState,
)
from airunner.utils.image import convert_binary_to_image


class CanvasHistoryMixin:
    """Mixin for canvas undo/redo history management."""

    def on_clear_history_signal(self) -> None:
        """Handle clear history signal."""
        self._clear_history()

    def on_action_undo_signal(self) -> None:
        """Handle undo action signal."""
        if not self.undo_history:
            return
        entry = self.undo_history.pop()
        self._apply_history_entry(entry, "before")
        self.redo_history.append(entry)
        self.api.art.canvas.update_history(
            len(self.undo_history), len(self.redo_history)
        )
        if self.views():
            view = self.views()[0]
            if hasattr(view, "updateImagePositions"):
                view.updateImagePositions()

    def on_action_redo_signal(self) -> None:
        """Handle redo action signal."""
        if not self.redo_history:
            return
        entry = self.redo_history.pop()
        self._apply_history_entry(entry, "after")
        self.undo_history.append(entry)
        self.api.art.canvas.update_history(
            len(self.undo_history), len(self.redo_history)
        )
        self._update_canvas_memory_allocation()
        if self.views():
            view = self.views()[0]
            if hasattr(view, "updateImagePositions"):
                view.updateImagePositions()

    def _apply_history_entry(self, entry: Dict[str, Any], target: str) -> None:
        """Apply history entry for undo/redo.

        Args:
            entry: History entry dict.
            target: Target state ("before" or "after").
        """
        entry_type = entry.get("type")
        if entry_type in {"layer_create", "layer_delete", "layer_reorder"}:
            self._apply_layer_structure(entry, target)
            return
        layer_id = entry.get("layer_id")
        state = entry.get(target)
        if state is None:
            return
        self._apply_layer_state(layer_id, state)
        self._refresh_layer_display()
        if self.api and hasattr(self.api, "art"):
            self.api.art.canvas.update_image_positions()
        self.update()
        for view in self.views():
            view.viewport().update()
            view.update()

    def _capture_layer_state(
        self, layer_id: Optional[int]
    ) -> Dict[str, Optional[Any]]:
        """Capture current state of a layer for history.

        Args:
            layer_id: ID of layer to capture, None for global.

        Returns:
            Dict with layer state.
        """
        if layer_id is None:
            settings = self.drawing_pad_settings
        else:
            settings = self._get_layer_specific_settings(
                DrawingPadSettings, layer_id=layer_id
            )

        if settings is None:
            return {"image": None, "mask": None, "x_pos": 0, "y_pos": 0}

        image_val = None
        try:
            current_selected = self._get_current_selected_layer_id()
        except Exception:
            current_selected = None

        if layer_id is None or layer_id == current_selected:
            if getattr(self, "_pending_image_binary", None) is not None:
                image_val = self._pending_image_binary
            elif (
                getattr(self, "_current_active_image_binary", None) is not None
            ):
                image_val = self._current_active_image_binary

        if image_val is None:
            image_val = getattr(settings, "image", None)

        mask_val = getattr(settings, "mask", None)

        # Extract dimensions from AIRAW1 binary to avoid re-parsing in memory tracker
        image_width = None
        image_height = None
        if (
            image_val
            and isinstance(image_val, bytes)
            and image_val.startswith(b"AIRAW1")
            and len(image_val) >= 14
        ):
            image_width = int.from_bytes(image_val[6:10], "big")
            image_height = int.from_bytes(image_val[10:14], "big")

        return {
            "image": image_val,
            "mask": mask_val,
            "x_pos": getattr(settings, "x_pos", 0) or 0,
            "y_pos": getattr(settings, "y_pos", 0) or 0,
            "text_items": getattr(settings, "text_items", None),
            "image_width": image_width,
            "image_height": image_height,
        }

    def _apply_layer_state(
        self, layer_id: Optional[int], state: Dict[str, Optional[Any]]
    ) -> None:
        """Apply layer state from history.

        Args:
            layer_id: ID of layer to apply state to.
            state: State dict to apply.
        """
        if layer_id is None:
            return

        updates: Dict[str, Optional[Any]] = {}
        for key in ("image", "mask", "x_pos", "y_pos"):
            if key in state:
                value = state[key]
                updates[key] = value

        if updates:
            self.update_drawing_pad_settings(layer_id=layer_id, **updates)

            image_data = state.get("image")
            try:
                current_layer = self._get_current_selected_layer_id()
                if layer_id == current_layer:
                    self._pending_image_binary = image_data
                    self._current_active_image_binary = image_data
            except Exception:
                pass

        layer_item = self._layer_items.get(layer_id)
        if layer_item is not None:
            image_data = state.get("image")
            if image_data is not None and len(image_data) > 0:
                pil_image = convert_binary_to_image(image_data)
                if pil_image is not None:
                    qimage = ImageQt.ImageQt(pil_image)
                    layer_item.updateImage(qimage)
            else:
                blank_qimage = self._create_blank_surface()
                layer_item.updateImage(blank_qimage)
            x_pos = state.get("x_pos")
            y_pos = state.get("y_pos")
            if x_pos is not None and y_pos is not None:
                canvas_offset = self.get_canvas_offset()
                try:
                    view = (
                        self.parent.views()[0]
                        if hasattr(self, "parent")
                        else None
                    )
                    grid_comp = (
                        view.grid_compensation_offset
                        if view
                        else QPointF(0, 0)
                    )
                except (AttributeError, IndexError):
                    grid_comp = QPointF(0, 0)

                manager = CanvasPositionManager()
                view_state = ViewState(
                    canvas_offset=canvas_offset, grid_compensation=grid_comp
                )

                abs_pos = QPointF(x_pos, y_pos)
                visible_pos = manager.absolute_to_display(abs_pos, view_state)

                layer_item.setPos(visible_pos)
                self.original_item_positions[layer_item] = QPointF(
                    x_pos, y_pos
                )

    def _begin_layer_history_transaction(
        self, layer_id: Optional[int], change_type: str
    ) -> None:
        """Begin layer history transaction.

        Args:
            layer_id: ID of layer, None for global.
            change_type: Type of change being made.
        """
        before_state = self._capture_layer_state(layer_id)
        self._history_transactions[layer_id] = {
            "type": change_type,
            "before": before_state,
        }

    def _commit_layer_history_transaction(
        self, layer_id: Optional[int], change_type: Optional[str] = None
    ) -> None:
        """Commit layer history transaction.

        Args:
            layer_id: ID of layer, None for global.
            change_type: Optional type override.
        """
        transaction = self._history_transactions.pop(layer_id, None)
        if transaction is None:
            return
        if change_type is not None:
            transaction["type"] = change_type
        after_state = self._capture_layer_state(layer_id)
        transaction["after"] = after_state

        if transaction["before"] == transaction["after"]:
            return

        entry = {
            "layer_id": layer_id,
            "type": transaction.get("type", "image"),
            "before": transaction["before"],
            "after": transaction["after"],
        }
        self.undo_history.append(entry)
        self.redo_history.clear()
        if self.api and hasattr(self.api, "art"):
            self.api.art.canvas.update_history(
                len(self.undo_history), len(self.redo_history)
            )
        # Defer memory allocation update to next event loop iteration
        # This allows the canvas to display the image immediately
        QTimer.singleShot(0, self._update_canvas_memory_allocation)

    def _cancel_layer_history_transaction(
        self, layer_id: Optional[int]
    ) -> None:
        """Cancel layer history transaction.

        Args:
            layer_id: ID of layer, None for global.
        """
        self._history_transactions.pop(layer_id, None)

    def _serialize_record(self, obj: Any) -> Optional[Dict[str, Any]]:
        """Serialize object to dict for storage.

        Args:
            obj: Object to serialize.

        Returns:
            Dict representation or None.
        """
        if obj is None:
            return None
        if is_dataclass(obj):
            return asdict(obj)
        if hasattr(obj, "to_dict"):
            try:
                return obj.to_dict()
            except Exception:
                pass
        if isinstance(obj, dict):
            return dict(obj)
        try:
            return dict(vars(obj))
        except Exception:
            return None

    def _clear_history(self) -> None:
        """Clear all undo/redo history."""
        self.undo_history = []
        self.redo_history = []
        self._history_transactions.clear()
        self._structure_history_transaction = None
        if self.api and hasattr(self.api, "art"):
            self.api.art.canvas.clear_history()

    def _add_image_to_undo(
        self,
        layer_id: Optional[int] = None,
        change_type: str = "image",
    ) -> Optional[int]:
        """Add image change to undo history.

        Args:
            layer_id: ID of layer, None for current.
            change_type: Type of change.

        Returns:
            Target layer ID used.
        """
        target_layer_id = layer_id
        if target_layer_id is None:
            target_layer_id = self._get_current_selected_layer_id()
        elif not isinstance(target_layer_id, int):
            target_layer_id = self._get_current_selected_layer_id()
        self._begin_layer_history_transaction(target_layer_id, change_type)
        return target_layer_id
