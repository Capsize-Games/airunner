from typing import List, Type, Optional, Dict, Any


from airunner.components.application.data import table_to_class
from airunner.components.llm.data.chatbot import Chatbot
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
        self.chatbot: Optional[Chatbot] = None
        # Cache for settings instances keyed by model class to avoid repeated DB reads
        self._settings_cache: Dict[Type[Any], Any] = {}
        # Cache for layer-specific settings instances keyed by string keys
        self._settings_cache_by_key: Dict[str, Any] = {}
        self._cached_send_image_to_canvas: List[Dict] = []

    @property
    def cached_send_image_to_canvas(self) -> List[Dict]:
        return self._cached_send_image_to_canvas

    @cached_send_image_to_canvas.setter
    def cached_send_image_to_canvas(self, value: List[Dict]) -> None:
        self._cached_send_image_to_canvas = value

    def get_cached_setting(self, model_class: Type[Any]) -> Optional[Any]:
        """Return a cached settings instance if present."""
        return self._settings_cache.get(model_class)

    def set_cached_setting(
        self, model_class: Type[Any], instance: Any
    ) -> None:
        """Store a settings instance in cache."""
        self._settings_cache[model_class] = instance

    def get_cached_setting_by_key(self, key: str) -> Optional[Any]:
        """Return a cached settings instance by string key if present."""
        return self._settings_cache_by_key.get(key)

    def set_cached_setting_by_key(self, key: str, instance: Any) -> None:
        """Store a settings instance in cache by string key."""
        self._settings_cache_by_key[key] = instance

    def invalidate_cached_setting(self, model_class: Type[Any]) -> None:
        """Remove a settings instance from cache."""
        self._settings_cache.pop(model_class, None)

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

        model_class = table_to_class.get(setting_name)
        if not model_class:
            # Fallback: attempt to find matching class by __tablename__ within cached classes
            for cls in list(self._settings_cache.keys()):
                try:
                    if getattr(cls, "__tablename__", None) == setting_name:
                        model_class = cls
                        break
                except Exception:
                    continue
            if not model_class:
                return

        cached = self.get_cached_setting(model_class)
        if cached is None:
            return

        if column_name:
            try:
                setattr(cached, column_name, val)
            except Exception:
                # If direct assignment fails for any reason, drop cache
                self.invalidate_cached_setting(model_class)
        else:
            # Unknown change scope; safest is to drop cache to force reload on next access
            self.invalidate_cached_setting(model_class)
