"""Mixin providing layer-specific settings management."""

from typing import Type, Any, Optional, List, Dict

from sqlalchemy.orm import joinedload

from airunner.components.data.session_manager import session_scope
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
        """Load layer-specific settings from database.

        Args:
            model_class_: SQLAlchemy model class for the settings table.
            layer_id: Layer ID to get settings for.
            eager_load: Optional list of relationship names to eager-load.

        Returns:
            Instance of the settings model for the specified layer.
        """
        try:
            with session_scope() as session:
                query = self._build_layer_query(
                    session, model_class_, layer_id, eager_load
                )
                settings_instance = query.first()

                if settings_instance is None:
                    settings_instance = self._create_layer_settings(
                        session, model_class_, layer_id, eager_load
                    )

                if settings_instance:
                    self._preload_attributes(settings_instance, model_class_)
                    session.expunge(settings_instance)

                return settings_instance

        except Exception as e:
            self.logger.error(
                f"Error loading layer settings for {model_class_.__name__} "
                f"layer {layer_id}: {e}"
            )
            return model_class_(layer_id=layer_id)

    def _build_layer_query(
        self,
        session: Any,
        model_class_: Type[Any],
        layer_id: int,
        eager_load: Optional[List[str]],
    ) -> Any:
        """Build SQLAlchemy query for layer-specific settings.

        Args:
            session: Database session.
            model_class_: Model class to query.
            layer_id: Layer ID to filter by.
            eager_load: Relationships to eager-load.

        Returns:
            Configured query object.
        """
        query = session.query(model_class_).filter(
            model_class_.layer_id == layer_id
        )

        if eager_load:
            for relation in eager_load:
                query = self._add_eager_load(query, model_class_, relation)

        return query

    def _add_eager_load(
        self, query: Any, model_class_: Type[Any], relation: str
    ) -> Any:
        """Add eager loading for a relationship to query.

        Args:
            query: Base query object.
            model_class_: Model class being queried.
            relation: Relationship name to eager-load.

        Returns:
            Query with eager loading added.
        """
        try:
            relation_attr = getattr(model_class_, relation, None)
            if relation_attr is not None:
                return query.options(joinedload(relation_attr))
        except Exception as e:
            self.logger.warning(
                f"Could not eager load {relation} for "
                f"{model_class_.__name__}: {e}"
            )
        return query

    def _create_layer_settings(
        self,
        session: Any,
        model_class_: Type[Any],
        layer_id: int,
        eager_load: Optional[List[str]],
    ) -> Any:
        """Create new layer-specific settings instance.

        Args:
            session: Database session.
            model_class_: Model class to create instance of.
            layer_id: Layer ID for new instance.
            eager_load: Relationships to load after creation.

        Returns:
            Created settings instance.
        """
        self.logger.info(
            f"Creating new layer settings for {model_class_.__name__} "
            f"layer {layer_id}"
        )
        settings_instance = model_class_(layer_id=layer_id)
        session.add(settings_instance)
        session.commit()

        if eager_load:
            query = self._build_layer_query(
                session, model_class_, layer_id, eager_load
            )
            settings_instance = query.first()

        return settings_instance

    def _preload_attributes(
        self, instance: Any, model_class_: Type[Any]
    ) -> None:
        """Pre-load commonly used attributes before session closes.

        Args:
            instance: Settings instance to pre-load.
            model_class_: Model class for logging.
        """
        try:
            for attr in ["x_pos", "y_pos", "strength", "scale"]:
                if hasattr(instance, attr):
                    _ = getattr(instance, attr)
        except Exception as e:
            self.logger.warning(
                f"Could not pre-load attributes for "
                f"{model_class_.__name__}: {e}"
            )
