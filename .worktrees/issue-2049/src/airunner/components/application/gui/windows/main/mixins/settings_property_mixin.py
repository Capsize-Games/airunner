"""Mixin providing property access to daemon-backed GUI resources."""

from typing import Any, Optional

from airunner.utils.settings import get_qsettings


_MAIN_TAB_INDEX_VERSION = 3


def _normalize_active_main_tab_index(settings: Any) -> int:
    """Normalize persisted main-tab indexes after tab removals."""
    active_index = settings.value("active_main_tab_index", 0, type=int)
    version = settings.value("main_tab_index_version", 1, type=int)
    if version < 2:
        if active_index == 2 or active_index >= 6:
            active_index = 0
        elif active_index > 2:
            active_index -= 1
    if version < _MAIN_TAB_INDEX_VERSION and active_index > 2:
        active_index = 0
    settings.setValue("active_main_tab_index", active_index)
    settings.setValue("main_tab_index_version", _MAIN_TAB_INDEX_VERSION)
    settings.sync()
    return active_index


class SettingsPropertyMixin:
    """Provides @property access to daemon-backed settings resources."""

    @property
    def stt_settings(self) -> Any:
        """Get STT (Speech-to-Text) settings."""
        return self._get_or_cache_settings("STTSettings")

    @property
    def application_settings(self) -> Any:
        """Get application-wide settings."""
        return self._get_or_cache_settings("ApplicationSettings")

    @property
    def language_settings(self) -> Any:
        """Get language/localization settings."""
        return self._get_or_cache_settings("LanguageSettings")

    @property
    def sound_settings(self) -> Any:
        """Get sound/audio settings."""
        return self._get_or_cache_settings("SoundSettings")

    @property
    def whisper_settings(self) -> Any:
        """Get Whisper STT model settings."""
        return self._get_or_cache_settings("WhisperSettings")

    @property
    def window_settings(self) -> Any:
        """Get window geometry and state settings from QSettings."""
        settings = get_qsettings()
        settings.beginGroup("window_settings")
        active_main_tab_index = _normalize_active_main_tab_index(settings)
        window_settings = self.resource_store.new_record(
            "WindowSettings",
            {
                "is_maximized": settings.value(
                    "is_maximized",
                    False,
                    type=bool,
                ),
                "is_fullscreen": settings.value(
                    "is_fullscreen",
                    False,
                    type=bool,
                ),
                "width": settings.value("width", 800, type=int),
                "height": settings.value("height", 600, type=int),
                "x_pos": settings.value("x_pos", 0, type=int),
                "y_pos": settings.value("y_pos", 0, type=int),
                "active_main_tab_index": active_main_tab_index,
            },
        )
        settings.endGroup()
        return window_settings

    @window_settings.setter
    def window_settings(self, settings_dict: dict):
        """Update window settings in QSettings."""
        settings = get_qsettings()
        settings.beginGroup("window_settings")
        for key, value in settings_dict.items():
            if key in ["is_maximized", "is_fullscreen"]:
                value = bool(value)
            else:
                value = int(value)
            settings.setValue(key, value)
        settings.setValue("main_tab_index_version", _MAIN_TAB_INDEX_VERSION)
        settings.endGroup()
        settings.sync()
        self._notify_setting_updated("WindowSettings", None, None)

    @property
    def rag_settings(self) -> Any:
        """Get RAG (Retrieval-Augmented Generation) settings."""
        rag_settings = self._get_or_cache_settings("RAGSettings")
        if getattr(rag_settings, "model_service", None) is None:
            from airunner.enums import ModelService

            rag_settings = self.resource_store.update_singleton(
                "RAGSettings",
                {
                    "model_service": ModelService.LOCAL.value,
                    "model_path": "",
                },
            )
            self.settings_mixin_shared_instance.set_cached_setting(
                "RAGSettings",
                rag_settings,
            )
        return rag_settings

    @property
    def llm_generator_settings(self) -> Any:
        """Get LLM generation settings."""
        settings = self._get_or_cache_settings("LLMGeneratorSettings")
        if settings is not None:
            if getattr(settings, "enable_tools", None) is None:
                settings.enable_tools = True
            if getattr(settings, "n_ctx", None) in (None, 0):
                settings.n_ctx = 32768
        return settings

    @property
    def generator_settings(self) -> Any:
        """Get Stable Diffusion generator settings."""
        return self._get_or_cache_settings(
            "GeneratorSettings",
            eager_load=["aimodel"],
        )

    @property
    def controlnet_settings(self) -> Any:
        """Get layer-specific ControlNet settings."""
        return self._get_layer_specific_settings("ControlnetSettings")

    @property
    def image_to_image_settings(self) -> Any:
        """Get layer-specific image-to-image settings."""
        return self._get_layer_specific_settings("ImageToImageSettings")

    @property
    def outpaint_settings(self) -> Any:
        """Get layer-specific outpaint settings."""
        return self._get_layer_specific_settings("OutpaintSettings")

    @property
    def drawing_pad_settings(self) -> Any:
        """Get layer-specific drawing pad settings."""
        return self._get_layer_specific_settings("DrawingPadSettings")

    @property
    def brush_settings(self) -> Any:
        """Get brush/drawing tool settings."""
        return self._get_or_cache_settings("BrushSettings")

    @property
    def metadata_settings(self) -> Any:
        """Get image metadata settings."""
        return self._get_or_cache_settings("MetadataSettings")

    @property
    def grid_settings(self) -> Any:
        """Get canvas grid display settings."""
        return self._get_or_cache_settings("GridSettings")

    @property
    def active_grid_settings(self) -> Any:
        """Get active grid configuration."""
        return self._get_or_cache_settings("ActiveGridSettings")

    @property
    def path_settings(self) -> Any:
        """Get file path settings."""
        return self._get_or_cache_settings("PathSettings")

    @property
    def memory_settings(self) -> Any:
        """Get memory/performance settings."""
        return self._get_or_cache_settings("MemorySettings")

    @property
    def chatbot_voice_settings(self) -> Any:
        """Get voice settings for current chatbot."""
        chatbot = self.chatbot
        if getattr(chatbot, "voice_id", None) is None:
            voice_settings = self.resource_store.first("VoiceSettings")
            if voice_settings is None:
                from airunner.enums import TTSModel as TTSModelEnum

                settings = self._get_settings_for_voice_model(
                    TTSModelEnum.ESPEAK
                )
                voice_settings = self.resource_store.create(
                    "VoiceSettings",
                    {
                        "name": "Default Voice",
                        "model_type": TTSModelEnum.ESPEAK.value,
                        "settings_id": settings.id,
                    },
                )
            chatbot = self.resource_store.update(
                "Chatbot",
                chatbot.id,
                {"voice_id": voice_settings.id},
            )
            self.settings_mixin_shared_instance.chatbot = chatbot

        voice_settings = self.resource_store.get(
            "VoiceSettings",
            self.chatbot.voice_id,
        )
        if voice_settings is None:
            raise ValueError(
                "Chatbot voice settings not found. Check database."
            )
        return voice_settings

    def _get_settings_for_voice_model(self, model_type) -> Any:
        """Get the settings object for one TTS model type."""
        from airunner.enums import TTSModel as TTSModelEnum

        if model_type == TTSModelEnum.ESPEAK:
            return self.espeak_settings
        if model_type == TTSModelEnum.OPENVOICE:
            return self.openvoice_settings
        return self.espeak_settings

    @property
    def chatbot_voice_model_type(self) -> Any:
        """Get TTS model type for current chatbot voice."""
        from airunner.enums import TTSModel

        return TTSModel(self.chatbot_voice_settings.model_type)

    def _get_active_voice_settings(
        self,
        resource_name: str,
        expected_model_type: str,
    ) -> Optional[Any]:
        """Return the settings row for the active chatbot voice when valid."""
        cached = self.settings_mixin_shared_instance.get_cached_setting(
            resource_name
        )

        voice_settings = None
        if getattr(self.chatbot, "voice_id", None) is not None:
            voice_settings = self.chatbot_voice_settings

        settings_id = None
        if (
            voice_settings is not None
            and voice_settings.model_type == expected_model_type
        ):
            settings_id = voice_settings.settings_id

        if cached is not None:
            if settings_id is None or getattr(cached, "id", None) == settings_id:
                return cached

        settings = None
        if settings_id is not None:
            settings = self.resource_store.get(resource_name, settings_id)
        if settings is None:
            settings = self.resource_store.first(resource_name)
        if settings is None:
            settings = self.resource_store.create(resource_name, {})

        self.settings_mixin_shared_instance.set_cached_setting(
            resource_name,
            settings,
        )
        return settings

    @property
    def espeak_settings(self) -> Optional[Any]:
        """Get eSpeak TTS engine settings."""
        return self._get_active_voice_settings(
            "EspeakSettings",
            "eSpeak",
        )

    @property
    def openvoice_settings(self) -> Any:
        """Get OpenVoice TTS model settings."""
        return self._get_active_voice_settings(
            "OpenVoiceSettings",
            "OpenVoice",
        )
