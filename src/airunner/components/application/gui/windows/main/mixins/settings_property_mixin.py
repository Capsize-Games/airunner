"""Mixin providing property access to all settings models using factory pattern.

This mixin uses lazy-loading via SettingsModelFactory to avoid importing
all model classes at module load time, reducing import overhead from 3.89s to ~0.02s.
"""

from typing import Any, Optional

from airunner.components.application.gui.windows.main.settings_model_factory import (
    get_settings_model,
)
from airunner.utils.settings import get_qsettings


class SettingsPropertyMixin:
    """Provides @property access to all settings models using factory pattern."""

    @property
    def stt_settings(self) -> Any:
        """Get STT (Speech-to-Text) settings."""
        return self._get_or_cache_settings(get_settings_model("STTSettings"))

    @property
    def application_settings(self) -> Any:
        """Get application-wide settings."""
        return self._get_or_cache_settings(
            get_settings_model("ApplicationSettings")
        )

    @property
    def language_settings(self) -> Any:
        """Get language/localization settings."""
        return self._get_or_cache_settings(
            get_settings_model("LanguageSettings")
        )

    @property
    def sound_settings(self) -> Any:
        """Get sound/audio settings."""
        return self._get_or_cache_settings(get_settings_model("SoundSettings"))

    @property
    def whisper_settings(self) -> Any:
        """Get Whisper STT model settings."""
        return self._get_or_cache_settings(
            get_settings_model("WhisperSettings")
        )

    @property
    def window_settings(self) -> Any:
        """Get window geometry and state settings from QSettings."""
        WindowSettings = get_settings_model("WindowSettings")
        settings = get_qsettings()
        settings.beginGroup("window_settings")
        window_settings = WindowSettings(
            is_maximized=settings.value("is_maximized", False, type=bool),
            is_fullscreen=settings.value("is_fullscreen", False, type=bool),
            width=settings.value("width", 800, type=int),
            height=settings.value("height", 600, type=int),
            x_pos=settings.value("x_pos", 0, type=int),
            y_pos=settings.value("y_pos", 0, type=int),
            active_main_tab_index=settings.value(
                "active_main_tab_index", 0, type=int
            ),
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
        settings.endGroup()
        settings.sync()
        self._notify_setting_updated(
            setting_name="window_settings", column_name=None, val=None
        )

    @property
    def rag_settings(self) -> Any:
        """Get RAG (Retrieval-Augmented Generation) settings."""
        RAGSettings = get_settings_model("RAGSettings")
        rag_settings = RAGSettings.objects.first()
        if rag_settings is None:
            from airunner.enums import ModelService

            RAGSettings.objects.create(
                enabled=False,
                model_service=ModelService.LOCAL.value,
                model_path="",
            )
            rag_settings = RAGSettings.objects.first()
        return rag_settings

    @property
    def llm_generator_settings(self) -> Any:
        """Get LLM generation settings."""
        return self._get_or_cache_settings(
            get_settings_model("LLMGeneratorSettings")
        )

    @property
    def generator_settings(self) -> Any:
        """Get Stable Diffusion generator settings."""
        return self._get_or_cache_settings(
            get_settings_model("GeneratorSettings"), eager_load=["aimodel"]
        )

    @property
    def controlnet_settings(self) -> Any:
        """Get layer-specific ControlNet settings."""
        return self._get_layer_specific_settings(
            get_settings_model("ControlnetSettings")
        )

    @property
    def image_to_image_settings(self) -> Any:
        """Get layer-specific image-to-image settings."""
        return self._get_layer_specific_settings(
            get_settings_model("ImageToImageSettings")
        )

    @property
    def outpaint_settings(self) -> Any:
        """Get layer-specific outpaint settings."""
        return self._get_layer_specific_settings(
            get_settings_model("OutpaintSettings")
        )

    @property
    def drawing_pad_settings(self) -> Any:
        """Get layer-specific drawing pad settings."""
        return self._get_layer_specific_settings(
            get_settings_model("DrawingPadSettings")
        )

    @property
    def brush_settings(self) -> Any:
        """Get brush/drawing tool settings."""
        return self._get_or_cache_settings(get_settings_model("BrushSettings"))

    @property
    def metadata_settings(self) -> Any:
        """Get image metadata settings."""
        return self._get_or_cache_settings(
            get_settings_model("MetadataSettings")
        )

    @property
    def grid_settings(self) -> Any:
        """Get canvas grid display settings."""
        return self._get_or_cache_settings(get_settings_model("GridSettings"))

    @property
    def active_grid_settings(self) -> Any:
        """Get active grid configuration."""
        return self._get_or_cache_settings(
            get_settings_model("ActiveGridSettings")
        )

    @property
    def path_settings(self) -> Any:
        """Get file path settings."""
        return self._get_or_cache_settings(get_settings_model("PathSettings"))

    @property
    def memory_settings(self) -> Any:
        """Get memory/performance settings."""
        return self._get_or_cache_settings(
            get_settings_model("MemorySettings")
        )

    @property
    def chatbot_voice_settings(self) -> Any:
        """Get voice settings for current chatbot."""
        VoiceSettings = get_settings_model("VoiceSettings")

        if self.chatbot.voice_id is None:
            voice_settings = VoiceSettings.objects.first()
            if voice_settings is None:
                from airunner.enums import TTSModel as TTSModelEnum

                settings = self._get_settings_for_voice_model(
                    TTSModelEnum.ESPEAK
                )
                voice_settings = VoiceSettings.objects.create(
                    name="Default Voice",
                    model_type=TTSModelEnum.ESPEAK.value,
                    settings_id=settings.id,
                )
            Chatbot = get_settings_model("Chatbot")
            Chatbot.objects.update(
                self.chatbot.id,
                voice_id=voice_settings.id,
            )
            self.chatbot.voice_id = voice_settings.id

        voice_settings = VoiceSettings.objects.get(pk=self.chatbot.voice_id)
        if voice_settings is None:
            raise ValueError(
                "Chatbot voice settings not found. Check database."
            )
        return voice_settings

    def _get_settings_for_voice_model(self, model_type) -> Any:
        """Get the appropriate settings object for a TTS model type.
        
        Args:
            model_type: TTSModel enum value
            
        Returns:
            Settings object for the specified TTS model type
        """
        from airunner.enums import TTSModel as TTSModelEnum
        
        if model_type == TTSModelEnum.ESPEAK:
            return self.espeak_settings
        elif model_type == TTSModelEnum.OPENVOICE:
            return self.openvoice_settings
        else:
            # Default to espeak
            return self.espeak_settings

    @property
    def chatbot_voice_model_type(self) -> Any:
        """Get TTS model type for current chatbot voice."""
        from airunner.enums import TTSModel

        return TTSModel(self.chatbot_voice_settings.model_type)

    @property
    def espeak_settings(self) -> Optional[Any]:
        """Get eSpeak TTS engine settings."""
        EspeakSettings = get_settings_model("EspeakSettings")
        cached = self.settings_mixin_shared_instance.get_cached_setting(
            EspeakSettings
        )
        if cached is not None:
            return cached
        settings = EspeakSettings.objects.first()
        if settings is None:
            settings = EspeakSettings.objects.create()
        self.settings_mixin_shared_instance.set_cached_setting(
            EspeakSettings, settings
        )
        return settings

    @property
    def openvoice_settings(self) -> Any:
        """Get OpenVoice TTS model settings."""
        OpenVoiceSettings = get_settings_model("OpenVoiceSettings")
        cached = self.settings_mixin_shared_instance.get_cached_setting(
            OpenVoiceSettings
        )
        if cached is not None:
            return cached
        settings = OpenVoiceSettings.objects.first()
        if settings is None:
            settings = OpenVoiceSettings.objects.create()
        self.settings_mixin_shared_instance.set_cached_setting(
            OpenVoiceSettings, settings
        )
        return settings
