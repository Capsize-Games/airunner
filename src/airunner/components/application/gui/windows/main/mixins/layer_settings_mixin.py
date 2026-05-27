"""Mixin providing layer-specific settings management."""

from typing import Type, Any, Optional, List, Dict

from airunner.components.application.gui.windows.main.settings_model_factory import (
    get_settings_model,
)
from airunner.utils.settings import get_qsettings


class LayerSettingsMixin:
    """Manages layer-specific settings and layer selection state."""

    def _get_layer_specific_settings(
        self,
        model_class_: Type[Any],
        layer_id: Optional[int] = None,
        eager_load: Optional[List[str]] = None,
    ) -> Any:
        """Get layer-specific settings instance.

        Args:
            model_class_: SQLAlchemy model class for the settings table.
            layer_id: Layer ID to get settings for. If None, gets settings
                for first selected layer.
            eager_load: Optional list of relationship names to eager-load.

        Returns:
            Instance of the settings model for the specified layer.
        """
        layer_id = self._resolve_layer_id(layer_id, model_class_)
        if layer_id is None:
            return model_class_()

        cache_key = f"{model_class_.__name__}_layer_{layer_id}"
        cached = self.settings_mixin_shared_instance.get_cached_setting_by_key(
            cache_key
        )
        if cached is not None:
            return cached

        instance = self._load_layer_settings_from_db(
            model_class_, layer_id, eager_load=eager_load
        )
        self.settings_mixin_shared_instance.set_cached_setting_by_key(
            cache_key, instance
        )
        return instance

    def _resolve_layer_id(
        self, layer_id: Optional[int], model_class_: Type[Any]
    ) -> Optional[int]:
        """Resolve layer ID from provided value or current selection.

        Args:
            layer_id: Explicit layer ID or None to use current selection.
            model_class_: Model class for fallback instance creation.

        Returns:
            Resolved layer ID or None.
        """
        if layer_id is not None:
            return layer_id

        layer_id = self._get_current_selected_layer_id()
        if layer_id is not None:
            return layer_id

        # Try to get first available layer
        CanvasLayer = get_settings_model("CanvasLayer")
        first_layer = CanvasLayer.objects.first()
        if first_layer:
            layer_id = first_layer.id
            self._selected_layer_ids.add(layer_id)
            return layer_id

        return None

    def _on_layer_selection_changed(self, data: Dict[str, Any]) -> None:
        """Handle layer selection changes from canvas layer container.

        Args:
            data: Dictionary containing selected_layer_ids list.
        """
        selected_layer_ids = data.get("selected_layer_ids", [])
        self._selected_layer_ids = set(selected_layer_ids)

        if not hasattr(self, "_qsettings_cache"):
            self._qsettings_cache = get_qsettings()

        if selected_layer_ids:
            self._qsettings_cache.setValue(
                "selected_layer_id", int(min(selected_layer_ids))
            )
        else:
            self._qsettings_cache.remove("selected_layer_id")

    def _get_current_selected_layer_id(self) -> Optional[int]:
        """Get the first selected layer ID from current UI state.

        Returns:
            The first selected layer ID, or None if no layers are selected.
        """
        if self._selected_layer_ids:
            return min(self._selected_layer_ids)

        if not hasattr(self, "_qsettings_cache"):
            self._qsettings_cache = get_qsettings()

        saved_layer_id = self._qsettings_cache.value(
            "selected_layer_id", None, type=int
        )
        if saved_layer_id is not None:
            self._selected_layer_ids.add(saved_layer_id)
            return saved_layer_id

        default_layer_id = self._get_first_layer_id()
        if default_layer_id is not None:
            self._selected_layer_ids.add(default_layer_id)
        return default_layer_id

    def _get_first_layer_id(self) -> Optional[int]:
        """Return the ID for the first persisted layer ordered by order.

        Returns:
            Layer ID or None if no layers exist.
        """
        try:
            CanvasLayer = get_settings_model("CanvasLayer")
            primary_layer = CanvasLayer.objects.filter_first(
                CanvasLayer.order == 0
            )
            if primary_layer is None:
                primary_layer = CanvasLayer.objects.first()
            return primary_layer.id if primary_layer else None
        except Exception as exc:
            self.logger.warning(
                "Unable to determine default layer id: %s", exc
            )
        return None

    def _load_layer_settings_from_db(
        self,
        model_class_: Type[Any],
        layer_id: int,
        eager_load: Optional[List[str]] = None,
    ) -> Any:
        """Load layer-specific settings through the daemon manager.

        Args:
            model_class_: SQLAlchemy model class for the settings table.
            layer_id: Layer ID to get settings for.
            eager_load: Optional list of relationship names to eager-load.

        Returns:
            Instance of the settings model for the specified layer.
        """
        try:
            settings_instance = model_class_.objects.filter_by_first(
                layer_id=layer_id,
                eager_load=eager_load,
            )
            if settings_instance is None:
                settings_instance = model_class_.objects.create(
                    layer_id=layer_id,
                )
                if settings_instance is None:
                    settings_instance = model_class_(layer_id=layer_id)
                elif eager_load:
                    settings_instance = model_class_.objects.filter_by_first(
                        layer_id=layer_id,
                        eager_load=eager_load,
                    ) or settings_instance
            return settings_instance
        except Exception as e:
            self.logger.error(
                f"Error loading layer settings for {model_class_.__name__} "
                f"layer {layer_id}: {e}"
            )
            return model_class_(layer_id=layer_id)
