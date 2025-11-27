"""Mixin for managing layer image items in CustomGraphicsView.

This mixin handles layer-specific image items, including removal and recentering.
"""

from typing import Dict
from PySide6.QtCore import QPointF

from airunner.components.art.data.canvas_layer import CanvasLayer
from airunner.components.art.data.drawingpad_settings import DrawingPadSettings
from airunner.components.art.gui.widgets.canvas.draggables.layer_image_item import (
    LayerImageItem,
)


class LayerItemManagementMixin:
    """Provides layer image item management for graphics view.

    This mixin manages:
    - Layer image item removal
    - Layer position recentering
    - Layer items collection

    Dependencies:
        - self.scene: CustomScene instance
        - self.logger: Logging instance
        - self.api: API instance
        - self.update_drawing_pad_settings(): Method to update settings
        - self.get_recentered_position(): Method to calculate centered position
    """

    @property
    def layers(self):
        """Get all layer items from the scene.

        Returns:
            List of layer items, or empty list if no scene.
        """
        if not self.scene or not hasattr(self.scene, "_layer_items"):
            return []
        return list(self.scene._layer_items.values())

    def _remove_layer_image_item(self, target):
        """Remove a layer image item and clear its persisted data.

        Handles removal of LayerImageItem instances, clearing their persisted
        images from the database and removing them from scene tracking.

        Args:
            target: The item to remove (LayerImageItem, scene item, or generic pixmap).
        """
        try:
            # If it's a LayerImageItem, clear the persisted layer image
            if isinstance(target, LayerImageItem):
                layer_id = getattr(target, "layer_id", None)
                try:
                    if target.scene():
                        target.scene().removeItem(target)
                except Exception:
                    pass

                # Remove from scene layer mapping
                try:
                    if self.scene and hasattr(self.scene, "_layer_items"):
                        for k, v in list(self.scene._layer_items.items()):
                            if v is target:
                                del self.scene._layer_items[k]
                                break
                except Exception:
                    pass

                # Clear persisted image for this layer
                try:
                    if layer_id is not None:
                        self.logger.info(
                            f"Clearing persisted image for layer {layer_id}"
                        )
                        self.update_drawing_pad_settings(
                            layer_id=layer_id, image=None
                        )

                        # Verify it was cleared
                        try:
                            settings = (
                                DrawingPadSettings.objects.filter_by_first(
                                    layer_id=layer_id
                                )
                            )
                            if settings:
                                has_image = settings.image is not None
                                self.logger.info(
                                    f"After clearing: layer {layer_id} still has image: {has_image}"
                                )
                            else:
                                self.logger.warning(
                                    f"No settings found for layer {layer_id} after update"
                                )
                        except Exception as e:
                            self.logger.exception(
                                f"Failed to verify image clear: {e}"
                            )

                        self.api.art.canvas.image_updated()
                except Exception as e:
                    self.logger.exception(
                        f"Failed to clear persisted image: {e}"
                    )
            # If it's the scene's primary item, use scene.delete_image()
            elif self.scene and getattr(self.scene, "item", None) is target:
                try:
                    self.scene.delete_image()
                except Exception:
                    try:
                        self.scene.current_active_image = None
                    except Exception:
                        pass
            # Generic pixmap: just remove it
            else:
                try:
                    if target.scene():
                        target.scene().removeItem(target)
                except Exception:
                    pass
        except Exception as e:
            self.logger.exception(f"Failed to remove layer image item: {e}")

    def recenter_layer_positions(self) -> Dict[str, QPointF]:
        """Recalculate and save new centered positions for all layers.

        This is used when explicitly recentering (e.g., clicking recenter button).
        It calculates new absolute positions centered in the viewport and saves them.

        Returns:
            Dict mapping scene items to their new QPointF positions.
        """
        layers = CanvasLayer.objects.order_by("order").all()
        self.logger.info(f"[RECENTER] Found {len(layers)} layers in database")
        new_positions = {}
        for layer in layers:
            self.logger.info(f"[RECENTER] Processing layer {layer.id}")
            results = DrawingPadSettings.objects.filter_by(layer_id=layer.id)
            self.logger.info(
                f"[RECENTER] Layer {layer.id}: found {len(results)} DrawingPadSettings"
            )
            if len(results) == 0:
                self.logger.warning(
                    f"[RECENTER] No DrawingPadSettings for layer {layer.id}"
                )
                continue

            drawingpad_settings = results[0]
            if not self.scene:
                self.logger.warning(f"[RECENTER] No scene!")
                continue

            self.logger.info(
                f"[RECENTER] Layer {layer.id}: _layer_items has {len(self.scene._layer_items)} items"
            )
            scene_item = self.scene._layer_items.get(layer.id)
            if scene_item is None:
                self.logger.warning(
                    f"[RECENTER] No scene_item for layer {layer.id} in _layer_items: {list(self.scene._layer_items.keys())}"
                )
                continue

            # Calculate new centered position - use the working area (active grid) position
            # so all layers align with the active grid, not centered based on their own size
            pos_x, pos_y = self.get_recentered_position(
                self.application_settings.working_width,
                self.application_settings.working_height,
            )

            # Save the new position to database
            DrawingPadSettings.objects.update(
                drawingpad_settings.id,
                x_pos=pos_x,
                y_pos=pos_y,
            )

            # Invalidate cache so next read gets fresh value from DB
            # This fixes the panning bug where stale cached positions were used
            cache_key = f"DrawingPadSettings_layer_{layer.id}"
            self.settings_mixin_shared_instance.invalidate_cached_setting_by_key(
                cache_key
            )

            new_positions[scene_item] = QPointF(pos_x, pos_y)
            self.logger.info(
                f"[RECENTER] Layer {layer.id}: saved to DB and dict - position x={pos_x}, y={pos_y}, scene_item id={id(scene_item)}"
            )

        self.logger.info(
            f"[RECENTER] Returning {len(new_positions)} positions"
        )
        return new_positions
