"""Mixin providing layer-specific settings update operations."""

from typing import Any, Dict, Type, Optional
from airunner.components.data.session_manager import session_scope
from airunner.components.art.data.controlnet_settings import (
    ControlnetSettings,
)
from airunner.components.art.data.brush_settings import BrushSettings
from airunner.components.art.data.image_to_image_settings import (
    ImageToImageSettings,
)
from airunner.components.art.data.outpaint_settings import (
    OutpaintSettings,
)
from airunner.components.art.data.drawingpad_settings import (
    DrawingPadSettings,
)
from airunner.components.art.data.metadata_settings import (
    MetadataSettings,
)


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
        self.update_layer_settings(ControlnetSettings, settings_dict, layer_id)

    def update_brush_settings(
        self, layer_id: Optional[int] = None, **settings_dict
    ) -> None:
        """Update brush settings for a specific layer.

        Args:
            layer_id: Layer ID to update. None uses current selected layer.
            **settings_dict: Settings to update as keyword arguments.
        """
        self.update_layer_settings(BrushSettings, settings_dict, layer_id)

    def update_image_to_image_settings(
        self, layer_id: Optional[int] = None, **settings_dict
    ) -> None:
        """Update image-to-image settings for a specific layer.

        Args:
            layer_id: Layer ID to update. None uses current selected layer.
            **settings_dict: Settings to update as keyword arguments.
        """
        self.update_layer_settings(
            ImageToImageSettings, settings_dict, layer_id
        )

    def update_outpaint_settings(
        self, layer_id: Optional[int] = None, **settings_dict
    ) -> None:
        """Update outpaint settings for a specific layer.

        Args:
            layer_id: Layer ID to update. None uses current selected layer.
            **settings_dict: Settings to update as keyword arguments.
        """
        self.update_layer_settings(OutpaintSettings, settings_dict, layer_id)

    def update_drawing_pad_settings(
        self, layer_id: Optional[int] = None, **settings_dict
    ) -> None:
        """Update drawing pad settings for a specific layer.

        Args:
            layer_id: Layer ID to update. None uses current selected layer.
            **settings_dict: Settings to update as keyword arguments.
        """
        self.update_layer_settings(DrawingPadSettings, settings_dict, layer_id)

    def update_metadata_settings(
        self, layer_id: Optional[int] = None, **settings_dict
    ) -> None:
        """Update metadata settings for a specific layer.

        Args:
            layer_id: Layer ID to update. None uses current selected layer.
            **settings_dict: Settings to update as keyword arguments.
        """
        self.update_layer_settings(MetadataSettings, settings_dict, layer_id)

    def update_layer_settings(
        self,
        model_class_: Type,
        updates: Dict[str, Any],
        layer_id: Optional[int] = None,
    ) -> None:
        """Update settings for a specific layer.

        Args:
            model_class_: SQLAlchemy model class for the settings table.
            updates: Dictionary of field updates.
            layer_id: Layer ID to update. None uses current selected layer.
        """
        resolved_layer_id = self._resolve_layer_id_for_update(layer_id)

        if resolved_layer_id is None:
            return self._fallback_to_global_update(model_class_, updates)

        self._update_layer_specific_settings(
            model_class_, updates, resolved_layer_id
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
        self, model_class_: Type, updates: Dict[str, Any]
    ) -> None:
        """Fall back to global settings update when no layer.

        Args:
            model_class_: SQLAlchemy model class.
            updates: Dictionary of updates.
        """
        self.logger.warning(
            f"No layer selected, falling back to global settings "
            f"update for {model_class_.__name__}"
        )
        return self.update_settings(model_class_, updates)

    def _update_layer_specific_settings(
        self,
        model_class_: Type,
        updates: Dict[str, Any],
        layer_id: int,
    ) -> None:
        """Update layer-specific settings in database.

        Args:
            model_class_: SQLAlchemy model class.
            updates: Dictionary of updates.
            layer_id: Layer ID to update.
        """
        try:
            with session_scope() as session:
                setting = self._get_or_create_layer_setting(
                    session, model_class_, layer_id, updates
                )
                self._apply_layer_updates(setting, model_class_, updates)
                session.commit()
                self._invalidate_layer_cache(model_class_, layer_id)
                self._notify_layer_updates(model_class_, updates)
        except Exception as e:
            self.logger.error(
                f"Failed to update layer-specific settings for "
                f"{model_class_.__name__} layer {layer_id}: {e}"
            )

    def _get_or_create_layer_setting(
        self, session, model_class_: Type, layer_id: int, updates: Dict
    ):
        """Get or create layer-specific setting.

        Args:
            session: Database session.
            model_class_: SQLAlchemy model class.
            layer_id: Layer ID.
            updates: Dictionary of updates.

        Returns:
            Setting instance.
        """
        setting = (
            session.query(model_class_)
            .filter(model_class_.layer_id == layer_id)
            .first()
        )

        if setting is None:
            setting = self._create_layer_setting(
                model_class_, layer_id, updates
            )
            session.add(setting)

        return setting

    def _create_layer_setting(
        self, model_class_: Type, layer_id: int, updates: Dict
    ):
        """Create new layer-specific setting.

        Args:
            model_class_: SQLAlchemy model class.
            layer_id: Layer ID.
            updates: Initial values.

        Returns:
            New setting instance.
        """
        self.logger.info(
            f"Creating new layer-specific settings for "
            f"{model_class_.__name__} layer {layer_id}"
        )
        return model_class_(layer_id=layer_id, **updates)

    def _apply_layer_updates(
        self, setting, model_class_: Type, updates: Dict[str, Any]
    ) -> None:
        """Apply updates to layer setting.

        Args:
            setting: Setting instance.
            model_class_: SQLAlchemy model class.
            updates: Dictionary of updates.
        """
        for key, value in updates.items():
            if hasattr(setting, key):
                setattr(setting, key, value)
            else:
                self.logger.warning(
                    f"Field {key} does not exist on "
                    f"{model_class_.__name__}"
                )

    def _invalidate_layer_cache(
        self, model_class_: Type, layer_id: int
    ) -> None:
        """Invalidate cache for layer-specific settings.

        Args:
            model_class_: SQLAlchemy model class.
            layer_id: Layer ID.
        """
        cache_key = f"{model_class_.__name__}_layer_{layer_id}"
        self.settings_mixin_shared_instance.invalidate_cached_setting_by_key(
            cache_key
        )

    def _notify_layer_updates(
        self, model_class_: Type, updates: Dict[str, Any]
    ) -> None:
        """Notify listeners of layer setting updates.

        Args:
            model_class_: SQLAlchemy model class.
            updates: Dictionary of updates.
        """
        for name, value in updates.items():
            self._notify_setting_updated(
                model_class_.__tablename__, name, value
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
