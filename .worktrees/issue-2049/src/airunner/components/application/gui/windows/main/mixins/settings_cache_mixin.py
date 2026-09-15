"""Mixin providing settings cache management functionality."""

from typing import Any, Optional, List


class SettingsCacheMixin:
    """Manages caching of settings instances to avoid repeated DB queries."""

    def clear_cache_settings(self) -> None:
        """Clear all cached settings instances."""
        self.settings_mixin_shared_instance._settings_cache.clear()
        self.settings_mixin_shared_instance._settings_cache_by_key.clear()

    def _get_or_cache_settings(
        self, resource_name: str, eager_load: Optional[List[str]] = None
    ) -> Any:
        """Get a settings instance from cache or load and cache it.

        Args:
            resource_name: Resource name for the daemon-backed settings row.
            eager_load: Optional list of relationship names to eager-load.

        Returns:
            Instance of the settings model.
        """
        cached = self.settings_mixin_shared_instance.get_cached_setting(
            resource_name
        )
        if cached is not None:
            return cached

        instance = self.load_settings_from_db(
            resource_name, eager_load=eager_load
        )
        self.settings_mixin_shared_instance.set_cached_setting(
            resource_name, instance
        )
        return instance

    def _invalidate_setting_cache(self, resource_name: str) -> None:
        """Invalidate cached setting for given model class.

        Args:
            resource_name: Resource name to invalidate.
        """
        self.settings_mixin_shared_instance.invalidate_cached_setting(
            resource_name
        )
