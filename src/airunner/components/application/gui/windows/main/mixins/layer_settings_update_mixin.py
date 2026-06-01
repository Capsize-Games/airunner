"""Mixin providing layer-specific settings update operations."""

from typing import Any, Dict, Optional


class LayerSettingsUpdateMixin:
    """Mixin for updating layer-specific settings."""

    def update_controlnet_settings(
        self, layer_id: Optional[int] = None, **settings_dict
    ) -> None:
        """Update ControlNet settings for a specific layer.

        Args:
            layer_id: Layer ID to update. None uses current selected layer.
            **settings_dict: Settings to update as keyword arguments.
        """
        self.update_layer_settings("ControlnetSettings", settings_dict, layer_id)

    def update_brush_settings(
        self, layer_id: Optional[int] = None, **settings_dict
    ) -> None:
        """Update brush settings for a specific layer.

        Args:
            layer_id: Layer ID to update. None uses current selected layer.
            **settings_dict: Settings to update as keyword arguments.
        """
        self.update_settings("BrushSettings", settings_dict)

    def update_image_to_image_settings(
        self, layer_id: Optional[int] = None, **settings_dict
    ) -> None:
        """Update image-to-image settings for a specific layer.

        Args:
            layer_id: Layer ID to update. None uses current selected layer.
            **settings_dict: Settings to update as keyword arguments.
        """
        self.update_layer_settings("ImageToImageSettings", settings_dict, layer_id)

    def update_outpaint_settings(
        self, layer_id: Optional[int] = None, **settings_dict
    ) -> None:
        """Update outpaint settings for a specific layer.

        Args:
            layer_id: Layer ID to update. None uses current selected layer.
            **settings_dict: Settings to update as keyword arguments.
        """
        self.update_layer_settings("OutpaintSettings", settings_dict, layer_id)

    def update_drawing_pad_settings(
        self, layer_id: Optional[int] = None, **settings_dict
    ) -> None:
        """Update drawing pad settings for a specific layer.

        Args:
            layer_id: Layer ID to update. None uses current selected layer.
            **settings_dict: Settings to update as keyword arguments.
        """
        self.update_layer_settings("DrawingPadSettings", settings_dict, layer_id)

    def update_metadata_settings(
        self, layer_id: Optional[int] = None, **settings_dict
    ) -> None:
        """Update metadata settings for a specific layer.

        Args:
            layer_id: Layer ID to update. None uses current selected layer.
            **settings_dict: Settings to update as keyword arguments.
        """
        self.update_layer_settings("MetadataSettings", settings_dict, layer_id)

    def update_layer_settings(
        self,
        resource_name: str,
        updates: Dict[str, Any],
        layer_id: Optional[int] = None,
    ) -> None:
        """Update settings for a specific layer.

        Args:
            resource_name: Resource name for the settings table.
            updates: Dictionary of field updates.
            layer_id: Layer ID to update. None uses current selected layer.
        """
        resolved_layer_id = self._resolve_layer_id_for_update(layer_id)

        if resolved_layer_id is None:
            return self._fallback_to_global_update(resource_name, updates)

        self._update_layer_specific_settings(
            resource_name,
            updates,
            resolved_layer_id,
        )

    def _resolve_layer_id_for_update(
        self, layer_id: Optional[int]
    ) -> Optional[int]:
        """Resolve layer ID for update operation.

        Args:
            layer_id: Provided layer ID or None.

        Returns:
            Resolved layer ID or None.
        """
        if layer_id is not None:
            return layer_id
        return self._get_current_selected_layer_id()

    def _fallback_to_global_update(
        self, resource_name: str, updates: Dict[str, Any]
    ) -> None:
        """Fall back to global settings update when no layer.

        Args:
            resource_name: Resource name.
            updates: Dictionary of updates.
        """
        self.logger.warning(
            f"No layer selected, falling back to global settings "
            f"update for {resource_name}"
        )
        return self.update_settings(resource_name, updates)

    def _update_layer_specific_settings(
        self,
        resource_name: str,
        updates: Dict[str, Any],
        layer_id: int,
    ) -> None:
        """Update layer-specific settings through the daemon manager.

        Args:
            resource_name: Resource name.
            updates: Dictionary of updates.
            layer_id: Layer ID to update.
        """
        try:
            self.resource_store.update_layer(resource_name, layer_id, updates)

            self._invalidate_layer_cache(resource_name, layer_id)
            self._notify_layer_updates(resource_name, updates)
        except Exception as e:
            self.logger.error(
                f"Failed to update layer-specific settings for "
                f"{resource_name} layer {layer_id}: {e}"
            )

    def _invalidate_layer_cache(
        self, resource_name: str, layer_id: int
    ) -> None:
        """Invalidate cache for layer-specific settings.

        Args:
            resource_name: Resource name.
            layer_id: Layer ID.
        """
        cache_key = f"{resource_name}_layer_{layer_id}"
        self.settings_mixin_shared_instance.invalidate_cached_setting_by_key(
            cache_key
        )

    def _notify_layer_updates(
        self, resource_name: str, updates: Dict[str, Any]
    ) -> None:
        """Notify listeners of layer setting updates.

        Args:
            resource_name: Resource name.
            updates: Dictionary of updates.
        """
        for name, value in updates.items():
            self._notify_setting_updated(
                resource_name, name, value
            )

    def _notify_setting_updated(
        self, table_name: str, column_name: str, value: Any
    ) -> None:
        """Notify that a setting was updated.

        Args:
            table_name: Database table name.
            column_name: Column name.
            value: New value.
        """
        # Placeholder for actual notification implementation
        # This would be __settings_updated in the original class
