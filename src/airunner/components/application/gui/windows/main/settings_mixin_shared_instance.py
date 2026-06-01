from typing import Any, Dict, List, Optional

from airunner.utils.application.get_logger import get_logger
from airunner.settings import AIRUNNER_LOG_LEVEL


class SettingsMixinSharedInstance:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(SettingsMixinSharedInstance, cls).__new__(
                cls, *args, **kwargs
            )
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self.logger = get_logger("AI Runner", AIRUNNER_LOG_LEVEL)

        self._initialized = True
        self.chatbot: Optional[Any] = None
        self.resource_store: Optional[Any] = None
        self._settings_cache: Dict[str, Any] = {}
        # Cache for layer-specific settings instances keyed by string keys
        self._settings_cache_by_key: Dict[str, Any] = {}
        self._cached_send_image_to_canvas: List[Dict] = []

    @property
    def cached_send_image_to_canvas(self) -> List[Dict]:
        return self._cached_send_image_to_canvas

    @cached_send_image_to_canvas.setter
    def cached_send_image_to_canvas(self, value: List[Dict]) -> None:
        self._cached_send_image_to_canvas = value

    @staticmethod
    def _cache_key(model_class_or_name: Any) -> str:
        if isinstance(model_class_or_name, str):
            return model_class_or_name
        return getattr(model_class_or_name, "__name__", str(model_class_or_name))

    def get_cached_setting(self, model_class_or_name: Any) -> Optional[Any]:
        """Return a cached settings instance if present."""
        return self._settings_cache.get(self._cache_key(model_class_or_name))

    def set_cached_setting(
        self, model_class_or_name: Any, instance: Any
    ) -> None:
        """Store a settings instance in cache."""
        self._settings_cache[self._cache_key(model_class_or_name)] = instance

    def get_cached_setting_by_key(self, key: str) -> Optional[Any]:
        """Return a cached settings instance by string key if present."""
        return self._settings_cache_by_key.get(key)

    def set_cached_setting_by_key(self, key: str, instance: Any) -> None:
        """Store a settings instance in cache by string key."""
        self._settings_cache_by_key[key] = instance

    def invalidate_cached_setting(self, model_class_or_name: Any) -> None:
        """Remove a settings instance from cache."""
        self._settings_cache.pop(self._cache_key(model_class_or_name), None)

    def invalidate_cached_setting_by_key(self, key: str) -> None:
        """Remove a settings instance from cache by string key."""
        self._settings_cache_by_key.pop(key, None)

    def on_settings_updated(
        self, setting_name: Optional[str], column_name: Optional[str], val: Any
    ) -> None:
        """Update or invalidate cache when settings change.

        Args:
            setting_name: Table name for the setting (SQLAlchemy __tablename__).
            column_name: Column updated, if any.
            val: New value for the column if column_name is provided.
        """
        if not setting_name:
            return

        cached = self.get_cached_setting(setting_name)
        if cached is None:
            return

        if column_name:
            try:
                setattr(cached, column_name, val)
            except Exception:
                self.invalidate_cached_setting(setting_name)
        else:
            self.invalidate_cached_setting(setting_name)
