"""Mixin providing settings cache management functionality."""

from typing import Type, Any, Optional, List


class SettingsCacheMixin:
    """Manages caching of settings instances to avoid repeated DB queries."""

    def clear_cache_settings(self) -> None:
        """Clear all cached settings instances."""
        self.settings_mixin_shared_instance._settings_cache.clear()
        self.settings_mixin_shared_instance._settings_cache_by_key.clear()

    def _get_or_cache_settings(
        self, model_class_: Type[Any], eager_load: Optional[List[str]] = None
    ) -> Any:
        """Get a settings instance from cache or load and cache it.

        Args:
            model_class_: SQLAlchemy model class for the settings table.
            eager_load: Optional list of relationship names to eager-load.

        Returns:
            Instance of the settings model.
        """
        cached = self.settings_mixin_shared_instance.get_cached_setting(
            model_class_
        )
        if cached is not None:
            return cached

        instance = self.load_settings_from_db(
            model_class_, eager_load=eager_load
        )
        self.settings_mixin_shared_instance.set_cached_setting(
            model_class_, instance
        )
        return instance

    def _invalidate_setting_cache(self, model_class_: Type[Any]) -> None:
        """Invalidate cached setting for given model class.

        Args:
            model_class_: SQLAlchemy model class to invalidate.
        """
        self.settings_mixin_shared_instance.invalidate_cached_setting(
            model_class_
        )
