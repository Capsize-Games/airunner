"""Mixin providing basic settings update operations."""

from typing import Any, Dict, Type, Optional
from airunner.components.settings.data.application_settings import (
    ApplicationSettings,
)
from airunner.components.tts.data.models.espeak_settings import EspeakSettings
from airunner.components.art.data.grid_settings import GridSettings
from airunner.components.art.data.active_grid_settings import (
    ActiveGridSettings,
)
from airunner.components.settings.data.path_settings import PathSettings
from airunner.components.art.data.memory_settings import MemorySettings
from airunner.components.llm.data.llm_generator_settings import (
    LLMGeneratorSettings,
)
from airunner.components.stt.data.whisper_settings import (
    WhisperSettings,
)
from airunner.components.art.data.generator_settings import (
    GeneratorSettings,
)
from airunner.components.art.data.controlnet_settings import (
    ControlnetSettings,
)
from airunner.components.art.data.saved_prompt import SavedPrompt
from airunner.components.settings.data.font_setting import FontSetting


class BasicSettingsUpdateMixin:
    """Mixin for updating non-layer-specific settings."""

    def update_application_settings(self, **settings_dict):
        """Update application settings.

        Args:
            **settings_dict: Settings to update as keyword arguments.
        """
        self.update_settings(ApplicationSettings, settings_dict)

    def update_espeak_settings(self, **settings_dict):
        """Update eSpeak TTS settings.

        Args:
            **settings_dict: Settings to update as keyword arguments.
        """
        self.update_settings(EspeakSettings, settings_dict)

    def update_grid_settings(self, **settings_dict):
        """Update grid settings.

        Args:
            **settings_dict: Settings to update as keyword arguments.
        """
        self.update_settings(GridSettings, settings_dict)

    def update_active_grid_settings(self, **settings_dict):
        """Update active grid settings.

        Args:
            **settings_dict: Settings to update as keyword arguments.
        """
        self.update_settings(ActiveGridSettings, settings_dict)

    def update_path_settings(self, **settings_dict):
        """Update path settings.

        Args:
            **settings_dict: Settings to update as keyword arguments.
        """
        self.update_settings(PathSettings, settings_dict)

    def update_memory_settings(self, **settings_dict):
        """Update memory settings.

        Args:
            **settings_dict: Settings to update as keyword arguments.
        """
        self.update_settings(MemorySettings, settings_dict)

    def update_llm_generator_settings(self, **settings_dict):
        """Update LLM generator settings.

        Args:
            **settings_dict: Settings to update as keyword arguments.
        """
        # Validate model_path to prevent corruption from SD/art/TTS model paths
        if "model_path" in settings_dict:
            model_path = settings_dict["model_path"]
            if model_path:
                invalid_patterns = [
                    "/art/models/",
                    "/txt2img",
                    "/inpaint",
                    "/tts/",
                    "/openvoice",
                    "/embedding/",
                ]
                for pattern in invalid_patterns:
                    if pattern in model_path:
                        self.logger.error(
                            f"Blocked invalid LLM model_path update: '{model_path}' "
                            f"contains invalid pattern '{pattern}'"
                        )
                        # Remove the invalid model_path from the update
                        del settings_dict["model_path"]
                        break
        
        self.update_settings(LLMGeneratorSettings, settings_dict)

    def update_whisper_settings(self, **settings_dict):
        """Update Whisper STT settings.

        Args:
            **settings_dict: Settings to update as keyword arguments.
        """
        self.update_settings(WhisperSettings, settings_dict)

    def update_generator_settings(self, **settings_dict):
        """Update generator settings.

        Args:
            **settings_dict: Settings to update as keyword arguments.
        """
        self.update_settings(GeneratorSettings, settings_dict)

    def update_controlnet_image_settings(self, **settings_dict):
        """Update ControlNet image settings.

        Args:
            **settings_dict: Settings to update as keyword arguments.
        """
        self.update_settings(ControlnetSettings, settings_dict)

    def update_settings(
        self, model_class_: Type, updates: Dict[str, Any]
    ) -> None:
        """Update settings for a given model class.

        Args:
            model_class_: SQLAlchemy model class to update.
            updates: Dictionary of field names to new values.
        """
        setting = self._get_or_create_setting(model_class_)
        if setting:
            self._apply_updates(model_class_, setting, updates)
        else:
            self.logger.error("Failed to update settings: No setting found")

    def update_saved_prompt(self, saved_prompt: SavedPrompt) -> None:
        """Update saved prompt in database.

        Args:
            saved_prompt: SavedPrompt instance to update.
        """
        existing = SavedPrompt.objects.filter_by_first(id=saved_prompt.id)
        if existing:
            self._update_prompt_attributes(existing, saved_prompt)
            existing.save()
        else:
            saved_prompt.save()
        self._notify_setting_updated(None, None, None)

    def update_font_setting(self, font_setting: FontSetting) -> None:
        """Update font setting in database.

        Args:
            font_setting: FontSetting instance to update.
        """
        existing = FontSetting.objects.filter_by_first(name=font_setting.name)
        if existing:
            self._update_font_attributes(existing, font_setting)
            existing.save()
        else:
            font_setting.save()
        self._notify_setting_updated(None, None, None)

    def _get_or_create_setting(self, model_class_: Type):
        """Get or create setting instance for model class.

        Args:
            model_class_: SQLAlchemy model class.

        Returns:
            Setting instance or None.
        """
        if model_class_.objects.first() is None:
            model_class_.objects.create()
        return model_class_.objects.order_by(model_class_.id.desc()).first()

    def _apply_updates(
        self, model_class_: Type, setting, updates: Dict[str, Any]
    ) -> None:
        """Apply updates to setting and notify listeners.

        Args:
            model_class_: SQLAlchemy model class.
            setting: Setting instance to update.
            updates: Dictionary of updates.
        """
        model_class_.objects.update(setting.id, **updates)

        # CRITICAL: Invalidate the settings cache for this model class
        # to ensure subsequent reads get the updated values from DB
        self._invalidate_setting_cache(model_class_)

        for name, value in updates.items():
            self._notify_setting_updated(
                model_class_.__tablename__, name, value
            )

    def _update_prompt_attributes(
        self, target: SavedPrompt, source: SavedPrompt
    ) -> None:
        """Copy attributes from source to target prompt.

        Args:
            target: Target prompt to update.
            source: Source prompt with new values.
        """
        for key in source.__dict__.keys():
            if key != "_sa_instance_state":
                setattr(target, key, getattr(source, key))

    def _update_font_attributes(
        self, target: FontSetting, source: FontSetting
    ) -> None:
        """Copy attributes from source to target font.

        Args:
            target: Target font to update.
            source: Source font with new values.
        """
        for key in source.__dict__.keys():
            if key != "_sa_instance_state":
                setattr(target, key, getattr(source, key))

    def _notify_setting_updated(
        self, table_name: Optional[str], column_name: Optional[str], value: Any
    ) -> None:
        """Notify that a setting was updated.

        Args:
            table_name: Database table name.
            column_name: Column name.
            value: New value.
        """
        # Placeholder for actual notification implementation
        # This would be __settings_updated in the original class
