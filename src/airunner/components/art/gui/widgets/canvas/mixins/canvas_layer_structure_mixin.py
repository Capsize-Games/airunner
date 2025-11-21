"""Canvas layer structure management mixin."""

from typing import List, Dict, Any, Iterable
from airunner.utils.application.mediator_mixin import MediatorMixin
from airunner.components.application.gui.windows.main.settings_mixin import (
    SettingsMixin,
)
from airunner.components.art.data.drawingpad_settings import DrawingPadSettings
from airunner.components.art.data.controlnet_settings import ControlnetSettings
from airunner.components.art.data.image_to_image_settings import (
    ImageToImageSettings,
)
from airunner.components.art.data.outpaint_settings import OutpaintSettings
from airunner.components.art.data.brush_settings import BrushSettings
from airunner.components.art.data.metadata_settings import MetadataSettings
from airunner.components.art.data.canvas_layer import CanvasLayer
from airunner.components.model_management.model_resource_manager import (
    ModelResourceManager,
)


class CanvasLayerStructureMixin(MediatorMixin, SettingsMixin):
    """Handles layer structure operations (create, delete, reorder).

    This mixin provides functionality for:
    - Capturing and restoring layer state snapshots
    - Managing layer structure transactions (undo/redo)
    - Removing layers and their associated settings
    - Coordinating layer order changes
    - Tracking canvas memory allocation
    """

    def _capture_layers_state(
        self, layer_ids: Iterable[int]
    ) -> List[Dict[str, Any]]:
        """Capture the current state of specified layers.

        Args:
            layer_ids: Layer IDs to capture.

        Returns:
            List of layer state snapshots as dicts.
        """
        snapshots: List[Dict[str, Any]] = []
        for layer_id in layer_ids:
            layer_record = self._serialize_record(
                CanvasLayer.objects.get(layer_id)
            )
            if layer_record is None:
                continue
            snapshot: Dict[str, Any] = {"layer": layer_record}
            snapshot["drawing_pad"] = self._serialize_record(
                DrawingPadSettings.objects.filter_by_first(layer_id=layer_id)
            )
            snapshot["controlnet"] = self._serialize_record(
                ControlnetSettings.objects.filter_by_first(layer_id=layer_id)
            )
            snapshot["image_to_image"] = self._serialize_record(
                ImageToImageSettings.objects.filter_by_first(layer_id=layer_id)
            )
            snapshot["outpaint"] = self._serialize_record(
                OutpaintSettings.objects.filter_by_first(layer_id=layer_id)
            )
            snapshot["brush"] = self._serialize_record(
                BrushSettings.objects.filter_by_first(layer_id=layer_id)
            )
            snapshot["metadata"] = self._serialize_record(
                MetadataSettings.objects.filter_by_first(layer_id=layer_id)
            )
            snapshots.append(snapshot)
        return snapshots

    def _merge_model_from_dict(self, model_cls, data: Dict[str, Any]) -> None:
        """Merge a model instance from a dict into the database.

        Args:
            model_cls: SQLAlchemy model class to merge.
            data: Dict of model attributes.
        """
        if not data:
            return
        try:
            model_instance = model_cls(**data)
            model_cls.objects.merge(model_instance)
        except Exception as exc:
            self.logger.error(
                "Failed to merge %s for layer operation: %s",
                model_cls.__name__,
                exc,
            )

    def _restore_layers_from_snapshots(
        self, snapshots: List[Dict[str, Any]]
    ) -> None:
        """Restore layers from snapshot data.

        Args:
            snapshots: List of layer state snapshots.
        """
        for snapshot in snapshots:
            layer_data = snapshot.get("layer")
            if layer_data:
                self._merge_model_from_dict(CanvasLayer, layer_data)
            self._merge_model_from_dict(
                DrawingPadSettings, snapshot.get("drawing_pad") or {}
            )
            self._merge_model_from_dict(
                ControlnetSettings, snapshot.get("controlnet") or {}
            )
            self._merge_model_from_dict(
                ImageToImageSettings, snapshot.get("image_to_image") or {}
            )
            self._merge_model_from_dict(
                OutpaintSettings, snapshot.get("outpaint") or {}
            )
            self._merge_model_from_dict(
                BrushSettings, snapshot.get("brush") or {}
            )
            self._merge_model_from_dict(
                MetadataSettings, snapshot.get("metadata") or {}
            )

    def _remove_layers(self, layer_ids: Iterable[int]) -> None:
        """Remove layers and their associated data.

        Args:
            layer_ids: Layer IDs to remove.
        """
        for layer_id in list(layer_ids):
            layer_item = self._layer_items.pop(layer_id, None)
            if layer_item is not None and layer_item.scene():
                layer_item.scene().removeItem(layer_item)
            self._history_transactions.pop(layer_id, None)
            self._original_item_positions = {
                item: pos
                for item, pos in self._original_item_positions.items()
                if getattr(item, "layer_id", None) != layer_id
            }

            # Clear layer-specific cache entries to prevent stale data
            cache_by_key = (
                self.settings_mixin_shared_instance._settings_cache_by_key
            )
            for model_class in [
                DrawingPadSettings,
                ControlnetSettings,
                ImageToImageSettings,
                OutpaintSettings,
                BrushSettings,
                MetadataSettings,
            ]:
                cache_key = f"{model_class.__name__}_layer_{layer_id}"
                cache_by_key.pop(cache_key, None)

            DrawingPadSettings.objects.delete(layer_id=layer_id)
            ControlnetSettings.objects.delete(layer_id=layer_id)
            ImageToImageSettings.objects.delete(layer_id=layer_id)
            OutpaintSettings.objects.delete(layer_id=layer_id)

    def _apply_layer_orders(self, orders: List[Dict[str, int]]) -> None:
        """Apply layer ordering from a list of order dicts.

        Args:
            orders: List of dicts with layer_id and order keys.
        """
        for entry in orders:
            layer_id = entry.get("layer_id")
            order_value = entry.get("order")
            if layer_id is None or order_value is None:
                continue
            CanvasLayer.objects.update(layer_id, order=order_value)

    def _begin_layer_structure_transaction(
        self, action: str, layer_ids: Iterable[int]
    ) -> None:
        """Begin a layer structure transaction for undo/redo.

        Args:
            action: Action type ("create", "delete", "reorder").
            layer_ids: Layer IDs involved in the transaction.
        """
        if not action:
            return
        self._structure_history_transaction = {
            "action": action,
            "layer_ids": list(layer_ids),
            "orders_before": self._capture_layer_orders(),
        }
        if action == "delete":
            self._structure_history_transaction["layers_before"] = (
                self._capture_layers_state(layer_ids)
            )

    def _commit_layer_structure_transaction(
        self, action: str, layer_ids: Iterable[int]
    ) -> None:
        """Commit a layer structure transaction to history.

        Args:
            action: Action type ("create", "delete", "reorder").
            layer_ids: Layer IDs involved in the transaction.
        """
        if not self._is_transaction_valid(action):
            return

        resolved_layer_ids = self._resolve_layer_ids(action, layer_ids)
        entry = self._create_history_entry(action, resolved_layer_ids)

        if self._should_skip_transaction(action, entry):
            self._structure_history_transaction = None
            return

        self._finalize_transaction(entry)

    def _is_transaction_valid(self, action: str) -> bool:
        """Check if transaction is valid for commit."""
        if self._structure_history_transaction is None:
            return False
        if self._structure_history_transaction.get("action") != action:
            self._structure_history_transaction = None
            return False
        return True

    def _resolve_layer_ids(
        self, action: str, layer_ids: Iterable[int]
    ) -> list[int]:
        """Resolve layer IDs for the transaction."""
        resolved = list(layer_ids)
        if action == "create":
            self._structure_history_transaction["layer_ids"] = resolved
        elif not resolved:
            resolved = list(
                self._structure_history_transaction.get("layer_ids", [])
            )
        return resolved

    def _create_history_entry(
        self, action: str, layer_ids: list[int]
    ) -> Dict[str, Any]:
        """Create history entry for transaction."""
        transaction = self._structure_history_transaction
        orders_after = self._capture_layer_orders()

        entry: Dict[str, Any] = {
            "type": f"layer_{action}",
            "layer_ids": layer_ids,
            "orders_before": transaction.get("orders_before", []),
            "orders_after": orders_after,
        }

        if action == "create":
            entry["layers_after"] = self._capture_layers_state(layer_ids)
        elif action == "delete":
            entry["layers_before"] = transaction.get("layers_before", [])

        return entry

    def _should_skip_transaction(
        self, action: str, entry: Dict[str, Any]
    ) -> bool:
        """Check if transaction should be skipped."""
        if (
            action == "reorder"
            and entry["orders_before"] == entry["orders_after"]
        ):
            return True
        if action == "create" and not entry.get("layers_after"):
            return True
        if action == "delete" and not entry.get("layers_before"):
            return True
        return False

    def _finalize_transaction(self, entry: Dict[str, Any]) -> None:
        """Finalize and store transaction in history."""
        self.undo_history.append(entry)
        self.redo_history.clear()
        self._structure_history_transaction = None

        if self.api and hasattr(self.api, "art"):
            self.api.art.canvas.update_history(
                len(self.undo_history), len(self.redo_history)
            )
        self._update_canvas_memory_allocation()

    def _update_canvas_memory_allocation(self):
        """Update ModelResourceManager with current canvas memory usage."""
        try:
            resource_manager = ModelResourceManager()
            # Use the cached tracker from ModelResourceManager for performance
            tracker = resource_manager.canvas_memory_tracker

            # Estimate memory used by canvas history
            vram_gb, ram_gb = tracker.estimate_history_memory(self)

            # Update the resource manager
            resource_manager.update_canvas_history_allocation(vram_gb, ram_gb)

        except Exception as e:
            # Don't let canvas memory tracking errors break the canvas
            self.logger.debug(
                f"Failed to update canvas memory allocation: {e}"
            )

    def _cancel_layer_structure_transaction(self) -> None:
        """Cancel the current layer structure transaction."""
        self._structure_history_transaction = None

    def _apply_layer_structure(
        self, entry: Dict[str, Any], target: str
    ) -> None:
        """Apply a layer structure entry (for undo/redo).

        Args:
            entry: History entry dict with layer operation details.
            target: "before" or "after" to determine which state to apply.
        """
        entry_type = entry.get("type")
        if entry_type not in {"layer_create", "layer_delete", "layer_reorder"}:
            return

        layer_ids = entry.get("layer_ids", [])
        orders = self._get_target_orders(entry, target)

        self._apply_layer_operation(entry_type, target, layer_ids, entry)

        if orders:
            self._apply_layer_orders(orders)

        self._finalize_layer_structure_change()

    def _get_target_orders(self, entry: Dict[str, Any], target: str) -> list:
        """Get layer orders for target state."""
        return (
            entry.get("orders_before", [])
            if target == "before"
            else entry.get("orders_after", [])
        )

    def _apply_layer_operation(
        self,
        entry_type: str,
        target: str,
        layer_ids: list[int],
        entry: Dict[str, Any],
    ) -> None:
        """Apply layer operation based on type and target."""
        if entry_type == "layer_create":
            if target == "before":
                self._remove_layers(layer_ids)
            else:
                self._restore_layers_from_snapshots(
                    entry.get("layers_after", [])
                )
        elif entry_type == "layer_delete":
            if target == "before":
                self._restore_layers_from_snapshots(
                    entry.get("layers_before", [])
                )
            else:
                self._remove_layers(layer_ids)

    def _finalize_layer_structure_change(self) -> None:
        """Finalize layer structure change by refreshing display."""
        self._refresh_layer_display()
        self.api.art.canvas.show_layers()
        if self.api and hasattr(self.api, "art"):
            self.api.art.canvas.update_history(
                len(self.undo_history), len(self.redo_history)
            )
