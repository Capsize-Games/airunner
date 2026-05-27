"""Mixin providing basic settings update operations."""

from typing import Any, Dict, Optional


class BasicSettingsUpdateMixin:
    """Mixin for updating non-layer-specific settings."""

    def update_application_settings(self, **settings_dict):
        """Update application settings.

        Args:
            **settings_dict: Settings to update as keyword arguments.
        """
        self.update_settings("ApplicationSettings", settings_dict)

    def update_espeak_settings(self, **settings_dict):
        """Update eSpeak TTS settings.

        Args:
            **settings_dict: Settings to update as keyword arguments.
        """
        self.update_settings("EspeakSettings", settings_dict)

    def update_grid_settings(self, **settings_dict):
        """Update grid settings.

        Args:
            **settings_dict: Settings to update as keyword arguments.
        """
        self.update_settings("GridSettings", settings_dict)

    def update_active_grid_settings(self, **settings_dict):
        """Update active grid settings.

        Args:
            **settings_dict: Settings to update as keyword arguments.
        """
        self.update_settings("ActiveGridSettings", settings_dict)

    def update_path_settings(self, **settings_dict):
        """Update path settings.

        Args:
            **settings_dict: Settings to update as keyword arguments.
        """
        self.update_settings("PathSettings", settings_dict)

    def update_memory_settings(self, **settings_dict):
        """Update memory settings.

        Args:
            **settings_dict: Settings to update as keyword arguments.
        """
        self.update_settings("MemorySettings", settings_dict)

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
        
        self.update_settings("LLMGeneratorSettings", settings_dict)

    def update_whisper_settings(self, **settings_dict):
        """Update Whisper STT settings.

        Args:
            **settings_dict: Settings to update as keyword arguments.
        """
        self.update_settings("WhisperSettings", settings_dict)

    def update_generator_settings(self, **settings_dict):
        """Update generator settings.

        Args:
            **settings_dict: Settings to update as keyword arguments.
        """
        self.update_settings("GeneratorSettings", settings_dict)

    def update_controlnet_image_settings(self, **settings_dict):
        """Update ControlNet image settings.

        Args:
            **settings_dict: Settings to update as keyword arguments.
        """
        self.update_controlnet_settings(**settings_dict)

    def update_settings(
        self, resource_name: str, updates: Dict[str, Any]
    ) -> None:
        """Update settings for a given model class.

        Args:
            resource_name: Resource name to update.
            updates: Dictionary of field names to new values.
        """
        setting = self._get_or_create_setting(resource_name)
        if setting:
            self._apply_updates(resource_name, setting, updates)
        else:
            self.logger.error("Failed to update settings: No setting found")

    def update_saved_prompt(self, saved_prompt: Any) -> None:
        """Update saved prompt in database.

        Args:
            saved_prompt: SavedPrompt instance to update.
        """
        existing = self.resource_store.first(
            "SavedPrompt",
            filters={"id": getattr(saved_prompt, "id", None)},
        )
        if existing:
            self._update_prompt_attributes(existing, saved_prompt)
            self.resource_store.update(
                "SavedPrompt",
                existing.id,
                self._record_values(existing),
            )
        else:
            self.resource_store.create(
                "SavedPrompt",
                self._record_values(saved_prompt),
            )
        self._notify_setting_updated(None, None, None)

    def update_font_setting(self, font_setting: Any) -> None:
        """Update font setting in database.

        Args:
            font_setting: FontSetting instance to update.
        """
        existing = self.resource_store.first(
            "FontSetting",
            filters={"name": getattr(font_setting, "name", None)},
        )
        if existing:
            self._update_font_attributes(existing, font_setting)
            self.resource_store.update(
                "FontSetting",
                existing.id,
                self._record_values(existing),
            )
        else:
            self.resource_store.create(
                "FontSetting",
                self._record_values(font_setting),
            )
        self._notify_setting_updated(None, None, None)

    def _get_or_create_setting(self, resource_name: str):
        """Get or create setting instance for model class.

        Args:
            resource_name: Resource name.

        Returns:
            Setting instance or None.
        """
        return self.resource_store.get_singleton(resource_name)

    def _apply_updates(
        self, resource_name: str, setting: Any, updates: Dict[str, Any]
    ) -> None:
        """Apply updates to setting and notify listeners.

        Args:
            resource_name: Resource name.
            setting: Setting instance to update.
            updates: Dictionary of updates.
        """
        if getattr(setting, "id", None) is not None:
            self.resource_store.update(resource_name, setting.id, updates)
        else:
            self.resource_store.update_singleton(resource_name, updates)

        self._invalidate_setting_cache(resource_name)

        for name, value in updates.items():
            self._notify_setting_updated(
                resource_name, name, value
            )

    def _update_prompt_attributes(
        self, target: Any, source: Any
    ) -> None:
        """Copy attributes from source to target prompt.

        Args:
            target: Target prompt to update.
            source: Source prompt with new values.
        """
        for key in source.__dict__.keys():
            if key != "_sa_instance_state":
                setattr(target, key, getattr(source, key))

    def _update_font_attributes(self, target: Any, source: Any) -> None:
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

    @staticmethod
    def _record_values(record: Any) -> Dict[str, Any]:
        values = getattr(record, "to_dict", lambda: dict(record.__dict__))()
        values.pop("id", None)
        values.pop("_sa_instance_state", None)
        return values
