"""Canvas layer management mixin.

This mixin provides layer management functionality for the canvas scene,
including layer visibility, deletion, reordering, and transaction management.
"""

from typing import List, Dict, Any, Iterable


from airunner.components.art.data.canvas_layer import CanvasLayer
from airunner.components.art.data.drawingpad_settings import (
    DrawingPadSettings,
)
from airunner.components.art.data.controlnet_settings import ControlnetSettings
from airunner.components.art.data.image_to_image_settings import (
    ImageToImageSettings,
)
from airunner.components.art.data.outpaint_settings import OutpaintSettings
from airunner.components.art.data.brush_settings import BrushSettings
from airunner.components.art.data.metadata_settings import MetadataSettings
from airunner.components.model_management import (
    ModelResourceManager,
)
from airunner.components.art.gui.widgets.canvas.draggables.layer_image_item import (
    LayerImageItem,
)
from airunner.utils.image import pil_to_qimage, convert_binary_to_image


class CanvasLayerMixin:
    """Mixin for canvas layer management operations.

    Handles layer visibility, deletion, reordering, and transaction-based
    layer structure changes with full undo/redo support.
    """

    def on_layer_visibility_toggled(self, data: Dict) -> None:
        """Handle layer visibility changes.

        Args:
            data: Dict with layer_id and visible flag.
        """
        layer_id = data.get("layer_id")
        visible = data.get("visible")

        self.logger.info(
            f"Layer visibility toggled: layer_id={layer_id}, visible={visible}"
        )

        if layer_id in self._layer_items:
            layer_item = self._layer_items[layer_id]
            try:
                layer_item.setVisible(visible)
                self.logger.info(f"Updated layer item visibility: {visible}")
                # Update text items associated with this layer
                self._update_layer_text_items_visibility(layer_id, visible)
            except RuntimeError as e:
                if "Internal C++ object" in str(
                    e
                ) and "already deleted" in str(e):
                    self.logger.warning(
                        f"Layer item {layer_id} was already deleted, removing from cache"
                    )
                    del self._layer_items[layer_id]
                    self._refresh_layer_display()
                else:
                    raise
        else:
            self.logger.warning(
                f"Layer item not found for layer_id={layer_id}"
            )
            self._refresh_layer_display()

    def _get_active_layer_item(self):
        """Get the graphics item for the currently selected layer.

        Returns:
            The LayerImageItem for the selected layer, or None if not found.
        """
        try:
            layer_id = self._get_current_selected_layer_id()
            if layer_id is not None and layer_id in self._layer_items:
                return self._layer_items[layer_id]
        except Exception:
            pass
        return None

    def _update_layer_text_items_visibility(
        self, layer_id: int, visible: bool
    ) -> None:
        """Update visibility of text items associated with a layer.

        Args:
            layer_id: ID of the layer.
            visible: Visibility flag to apply.
        """
        try:
            views = self.views()
            if views:
                view = views[0]
                text_map = getattr(view, "_text_item_layer_map", None)
                if text_map:
                    for item, lid in list(text_map.items()):
                        try:
                            if lid == layer_id:
                                item.setVisible(visible)
                        except Exception:
                            continue
        except Exception:
            pass

    def on_layer_deleted(self, data: Dict) -> None:
        """Handle layer deletion by removing its graphics item.

        Args:
            data: Dict with layer_id to delete.
        """
        layer_id = data.get("layer_id")

        if layer_id in self._layer_items:
            layer_item = self._layer_items[layer_id]
            try:
                if layer_item.scene():
                    layer_item.scene().removeItem(layer_item)
            except RuntimeError as e:
                if "Internal C++ object" in str(
                    e
                ) and "already deleted" in str(e):
                    self.logger.info(
                        f"Layer item {layer_id} was already deleted from Qt side"
                    )
                else:
                    self.logger.warning(
                        f"Error removing layer item {layer_id}: {e}"
                    )
            finally:
                del self._layer_items[layer_id]

    def on_layer_reordered(self, data: Dict) -> None:
        """Handle layer reordering by updating z-values.

        Args:
            data: Dict with reordering information.
        """
        self._refresh_layer_display()

    def on_layers_show_signal(self, data: Dict = None) -> None:
        """Handle layer container refresh signal.

        Args:
            data: Optional data dict.
        """
        self._current_active_image_ref = None
        self._refresh_layer_display()

    def _refresh_layer_display(self) -> None:
        """Refresh the display of all visible layers on the canvas.

        Only the main drawing pad scene and brush scene should render
        global layers; auxiliary scenes manage a single image item.
        """
        if getattr(self, "is_dragging", False):
            return

        canvas_type = getattr(self, "canvas_type", None)
        if canvas_type not in ("drawing_pad", "brush"):
            return

        layers = CanvasLayer.objects.order_by("order").all()
        layer_data = self._extract_layer_data(layers)

        self._remove_legacy_item(layer_data)
        self._remove_orphaned_layer_items(layer_data)
        self._update_or_create_layer_items(layer_data)

    def _extract_layer_data(self, layers) -> List[Dict[str, Any]]:
        """Extract layer data while session is active.

        Args:
            layers: Query result of CanvasLayer objects.

        Returns:
            List of dicts with layer properties.
        """
        layer_data = []
        for layer in layers:
            layer_data.append(
                {
                    "id": layer.id,
                    "visible": layer.visible,
                    "opacity": layer.opacity,
                    "order": layer.order,
                }
            )
        return layer_data

    def _remove_legacy_item(self, layer_data: List[Dict]) -> None:
        """Remove old drawing pad item to prevent duplication.

        Args:
            layer_data: List of layer data dicts.
        """
        if (
            len(layer_data) > 0
            and hasattr(self, "item")
            and self.item is not None
        ):
            try:
                if self.item.scene():
                    self.removeItem(self.item)
            except (RuntimeError, AttributeError) as e:
                self.logger.debug(f"Could not remove legacy item: {e}")
            self.item = None

    def _remove_orphaned_layer_items(self, layer_data: List[Dict]) -> None:
        """Remove layer items that no longer exist in database.

        Args:
            layer_data: List of current layer data dicts.
        """
        existing_layer_ids = {data["id"] for data in layer_data}
        items_to_remove = [
            layer_id
            for layer_id in self._layer_items
            if layer_id not in existing_layer_ids
        ]

        for layer_id in items_to_remove:
            item = self._layer_items[layer_id]
            try:
                if item.scene():
                    item.scene().removeItem(item)
            except (RuntimeError, AttributeError):
                pass
            del self._layer_items[layer_id]

    def _update_or_create_layer_items(self, layer_data: List[Dict]) -> None:
        """Update existing layer items or create new ones.

        Args:
            layer_data: List of layer data dicts.
        """
        for data in layer_data:
            layer_id = data["id"]
            if layer_id in self._layer_items:
                self._update_existing_layer_item(layer_id, data)
            else:
                self._create_new_layer_item(layer_id, data)

    def _update_existing_layer_item(self, layer_id: int, data: Dict) -> None:
        """Update properties of existing layer item.

        Args:
            layer_id: ID of the layer.
            data: Dict with layer properties.
        """
        item = self._layer_items[layer_id]
        try:
            item.setVisible(data["visible"])
            item.setOpacity(data["opacity"])
            item.setZValue(data["order"])

            # Reload image from database in case it changed (e.g., from drop/paste)
            drawing_pad = DrawingPadSettings.objects.filter_by_first(
                layer_id=layer_id
            )
            if drawing_pad and drawing_pad.image:
                image = convert_binary_to_image(drawing_pad.image)
                if image is not None:
                    qimage = pil_to_qimage(image)
                    if qimage is not None:
                        item.updateImage(qimage)
        except RuntimeError as e:
            if "Internal C++ object" in str(e) and "already deleted" in str(e):
                del self._layer_items[layer_id]

    def _create_new_layer_item(self, layer_id: int, data: Dict) -> None:
        """Create new layer item and add to scene.

        Args:
            layer_id: ID of the layer.
            data: Dict with layer properties.
        """
        layer_record = CanvasLayer.objects.get(layer_id)
        if not layer_record:
            return

        # Get the image from DrawingPadSettings for this layer
        drawing_pad = DrawingPadSettings.objects.filter_by_first(
            layer_id=layer_id
        )
        if not drawing_pad or not drawing_pad.image:
            return

        image = convert_binary_to_image(drawing_pad.image)
        if image is None:
            return

        qimage = pil_to_qimage(image)
        if qimage is None:
            return

        item = LayerImageItem(
            qimage,
            layer_id=layer_id,
            layer_image_data=data,
        )
        item.setVisible(data["visible"])
        item.setOpacity(data["opacity"])
        item.setZValue(data["order"])
        self.addItem(item)
        self._layer_items[layer_id] = item

    def on_layer_operation_begin(self, data: Dict[str, Any]) -> None:
        """Begin layer operation transaction.

        Args:
            data: Dict with action and layer_ids.
        """
        action = data.get("action")
        layer_ids = data.get("layer_ids") or []
        self._begin_layer_structure_transaction(action, layer_ids)

    def on_layer_operation_commit(self, data: Dict[str, Any]) -> None:
        """Commit layer operation transaction.

        Args:
            data: Dict with action and layer_ids.
        """
        action = data.get("action")
        layer_ids = data.get("layer_ids") or []
        self._commit_layer_structure_transaction(action, layer_ids)

    def on_layer_operation_cancel(self, data: Dict[str, Any]) -> None:
        """Cancel layer operation transaction.

        Args:
            data: Dict (unused).
        """
        self._cancel_layer_structure_transaction()

    def _begin_layer_structure_transaction(
        self, action: str, layer_ids: Iterable[int]
    ) -> None:
        """Begin layer structure transaction for undo/redo.

        Args:
            action: Action type (create, delete, reorder).
            layer_ids: IDs of affected layers.
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
        """Commit layer structure transaction to history.

        Args:
            action: Action type (create, delete, reorder).
            layer_ids: IDs of affected layers.
        """
        if self._structure_history_transaction is None:
            return
        transaction = self._structure_history_transaction
        if transaction.get("action") != action:
            self._structure_history_transaction = None
            return

        resolved_layer_ids = list(layer_ids)
        if action == "create":
            transaction["layer_ids"] = resolved_layer_ids
        elif not resolved_layer_ids:
            resolved_layer_ids = list(transaction.get("layer_ids", []))

        orders_after = self._capture_layer_orders()
        entry: Dict[str, Any] = {
            "type": f"layer_{action}",
            "layer_ids": resolved_layer_ids,
            "orders_before": transaction.get("orders_before", []),
            "orders_after": orders_after,
        }

        if action == "create":
            entry["layers_after"] = self._capture_layers_state(
                resolved_layer_ids
            )
        elif action == "delete":
            entry["layers_before"] = transaction.get("layers_before", [])

        # Skip if no meaningful change occurred
        if not self._is_valid_transaction(action, entry):
            self._structure_history_transaction = None
            return

        self.undo_history.append(entry)
        self.redo_history.clear()
        self._structure_history_transaction = None

        if self.api and hasattr(self.api, "art"):
            self.api.art.canvas.update_history(
                len(self.undo_history), len(self.redo_history)
            )

        self._update_canvas_memory_allocation()

    def _is_valid_transaction(
        self, action: str, entry: Dict[str, Any]
    ) -> bool:
        """Check if transaction represents a meaningful change.

        Args:
            action: Action type.
            entry: Transaction entry dict.

        Returns:
            True if transaction is valid, False otherwise.
        """
        if action == "reorder" and (
            entry["orders_before"] == entry["orders_after"]
        ):
            return False
        if action == "create" and not entry.get("layers_after"):
            return False
        if action == "delete" and not entry.get("layers_before"):
            return False
        return True

    def _update_canvas_memory_allocation(self) -> None:
        """Update ModelResourceManager with current canvas memory usage."""
        try:
            resource_manager = ModelResourceManager()
            # Use the cached tracker from ModelResourceManager for performance
            tracker = resource_manager.canvas_memory_tracker
            vram_gb, ram_gb = tracker.estimate_history_memory(self)
            resource_manager.update_canvas_history_allocation(vram_gb, ram_gb)
        except Exception as e:
            self.logger.debug(
                f"Failed to update canvas memory allocation: {e}"
            )

    def _cancel_layer_structure_transaction(self) -> None:
        """Cancel current layer structure transaction."""
        self._structure_history_transaction = None

    def _apply_layer_structure(
        self, entry: Dict[str, Any], target: str
    ) -> None:
        """Apply layer structure change for undo/redo.

        Args:
            entry: History entry dict.
            target: Target state ("before" or "after").
        """
        entry_type = entry.get("type")
        if entry_type not in {
            "layer_create",
            "layer_delete",
            "layer_reorder",
        }:
            return

        layer_ids = entry.get("layer_ids", [])
        orders = (
            entry.get("orders_before", [])
            if target == "before"
            else entry.get("orders_after", [])
        )

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

        if orders:
            self._apply_layer_orders(orders)

        self._refresh_layer_display()
        self.api.art.canvas.show_layers()
        if self.api and hasattr(self.api, "art"):
            self.api.art.canvas.update_image_positions()

    def _capture_layer_orders(self) -> List[Dict[str, int]]:
        """Capture current layer order state.

        Returns:
            List of dicts with layer_id and order.
        """
        layers = CanvasLayer.objects.all()
        if not layers:
            return []
        sorted_layers = sorted(
            layers, key=lambda layer: getattr(layer, "order", 0)
        )
        orders: List[Dict[str, int]] = []
        for index, layer in enumerate(sorted_layers):
            layer_id = getattr(layer, "id", None)
            if layer_id is None:
                continue
            order_value = getattr(layer, "order", index)
            orders.append({"layer_id": layer_id, "order": order_value})
        return orders

    def _capture_layers_state(
        self, layer_ids: Iterable[int]
    ) -> List[Dict[str, Any]]:
        """Capture full state of layers for undo/redo.

        Args:
            layer_ids: IDs of layers to capture.

        Returns:
            List of snapshot dicts with layer and settings data.
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

    def _restore_layers_from_snapshots(
        self, snapshots: List[Dict[str, Any]]
    ) -> None:
        """Restore layers from snapshot data.

        Args:
            snapshots: List of snapshot dicts with layer data.
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

    def _merge_model_from_dict(self, model_cls, data: Dict[str, Any]) -> None:
        """Merge model instance from dict data.

        Args:
            model_cls: Model class to instantiate.
            data: Dict with model field data.
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

    def _remove_layers(self, layer_ids: Iterable[int]) -> None:
        """Remove layers and their associated data.

        Args:
            layer_ids: IDs of layers to remove.
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

            # Clear layer-specific cache entries
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
        """Apply layer order changes to database.

        Args:
            orders: List of dicts with layer_id and order.
        """
        for entry in orders:
            layer_id = entry.get("layer_id")
            order_value = entry.get("order")
            if layer_id is None or order_value is None:
                continue
            CanvasLayer.objects.update(layer_id, order=order_value)
