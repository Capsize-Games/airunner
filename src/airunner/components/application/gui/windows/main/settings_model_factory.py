"""Factory for lazy-loading settings model classes.

This factory provides on-demand imports of settings model classes to avoid
the 3.89s import time penalty of importing all models at module load time.

Models are imported once and cached, so there's no performance penalty on
subsequent access. This is compatible with PyInstaller/Nuitka since the
imports are still present in the source code.
"""

from typing import Type, Any, Dict


class SettingsModelFactory:
    """Factory for lazy-loading settings model classes."""

    _instance = None
    _cache: Dict[str, Type[Any]] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def get_model(cls, model_name: str) -> Type[Any]:
        """Get a settings model class by name, importing and caching it.

        Args:
            model_name: Name of the model class to import.

        Returns:
            The model class.

        Raises:
            ValueError: If model_name is not recognized.
        """
        if model_name in cls._cache:
            return cls._cache[model_name]

        # Import mapping - add new models here
        import_map = {
            "STTSettings": "airunner.components.stt.data.stt_settings",
            "ApplicationSettings": "airunner.components.settings.data.application_settings",
            "LanguageSettings": "airunner.components.settings.data.language_settings",
            "SoundSettings": "airunner.components.settings.data.sound_settings",
            "WhisperSettings": "airunner.components.stt.data.whisper_settings",
            "WindowSettings": "airunner.components.settings.data.window_settings",
            "RAGSettings": "airunner.components.llm.data.rag_settings",
            "LLMGeneratorSettings": "airunner.components.llm.data.llm_generator_settings",
            "GeneratorSettings": "airunner.components.art.data.generator_settings",
            "ControlnetSettings": "airunner.components.art.data.controlnet_settings",
            "ImageToImageSettings": "airunner.components.art.data.image_to_image_settings",
            "OutpaintSettings": "airunner.components.art.data.outpaint_settings",
            "DrawingPadSettings": "airunner.components.art.data.drawingpad_settings",
            "BrushSettings": "airunner.components.art.data.brush_settings",
            "MetadataSettings": "airunner.components.art.data.metadata_settings",
            "GridSettings": "airunner.components.art.data.grid_settings",
            "ActiveGridSettings": "airunner.components.art.data.active_grid_settings",
            "PathSettings": "airunner.components.settings.data.path_settings",
            "MemorySettings": "airunner.components.art.data.memory_settings",
            "VoiceSettings": "airunner.components.settings.data.voice_settings",
            "EspeakSettings": "airunner.components.tts.data.models.espeak_settings",
            "OpenVoiceSettings": "airunner.components.tts.data.models.openvoice_settings",
            "Chatbot": "airunner.components.llm.data.chatbot",
            "CanvasLayer": "airunner.components.art.data.canvas_layer",
            "AIModels": "airunner.components.art.data.ai_models",
            "Schedulers": "airunner.components.art.data.schedulers",
            "User": "airunner.components.user.data.user",
            "Embedding": "airunner.components.art.data.embedding",
            "Lora": "airunner.components.art.data.lora",
            "SavedPrompt": "airunner.components.art.data.saved_prompt",
            "PromptTemplate": "airunner.components.llm.data.prompt_template",
            "ControlnetModel": "airunner.components.art.data.controlnet_model",
            "ImageFilterValue": "airunner.components.art.data.image_filter_value",
            "PipelineModel": "airunner.components.models.data.pipeline_model",
            "TargetFiles": "airunner.components.llm.data.target_files",
            "FontSetting": "airunner.components.settings.data.font_setting",
        }

        if model_name not in import_map:
            raise ValueError(
                f"Unknown model: {model_name}. "
                f"Available models: {', '.join(sorted(import_map.keys()))}"
            )

        # Import and cache the model
        module_path = import_map[model_name]
        module = __import__(module_path, fromlist=[model_name])
        model_class = getattr(module, model_name)
        cls._cache[model_name] = model_class
        return model_class

    @classmethod
    def clear_cache(cls):
        """Clear the cached models (useful for testing)."""
        cls._cache.clear()


# Convenience functions for common models
def get_settings_model(model_name: str) -> Type[Any]:
    """Get a settings model class by name.

    Args:
        model_name: Name of the model class (e.g., "STTSettings").

    Returns:
        The model class.
    """
    return SettingsModelFactory.get_model(model_name)
