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
            "STTSettings": "airunner.models.stt_settings",
            "ApplicationSettings": "airunner.models.application_settings",
            "LanguageSettings": "airunner.models.language_settings",
            "SoundSettings": "airunner.models.sound_settings",
            "WhisperSettings": "airunner.models.whisper_settings",
            "WindowSettings": "airunner.models.window_settings",
            "RAGSettings": "airunner.models.rag_settings",
            "LLMGeneratorSettings": "airunner.models.llm_generator_settings",
            "GeneratorSettings": "airunner.models.generator_settings",
            "ControlnetSettings": "airunner.models.controlnet_settings",
            "ImageToImageSettings": "airunner.models.image_to_image_settings",
            "OutpaintSettings": "airunner.models.outpaint_settings",
            "DrawingPadSettings": "airunner.models.drawingpad_settings",
            "BrushSettings": "airunner.models.brush_settings",
            "MetadataSettings": "airunner.models.metadata_settings",
            "GridSettings": "airunner.models.grid_settings",
            "ActiveGridSettings": "airunner.models.active_grid_settings",
            "PathSettings": "airunner.models.path_settings",
            "MemorySettings": "airunner.models.memory_settings",
            "VoiceSettings": "airunner.models.voice_settings",
            "EspeakSettings": "airunner.models.espeak_settings",
            "OpenVoiceSettings": "airunner.models.openvoice_settings",
            "Chatbot": "airunner.models.chatbot",
            "CanvasLayer": "airunner.models.canvas_layer",
            "AIModels": "airunner.models.ai_models",
            "Schedulers": "airunner.models.schedulers",
            "User": "airunner.models.user",
            "Embedding": "airunner.models.embedding",
            "Lora": "airunner.models.lora",
            "SavedPrompt": "airunner.models.saved_prompt",
            "PromptTemplate": "airunner.models.prompt_template",
            "ControlnetModel": "airunner.models.controlnet_model",
            "ImageFilterValue": "airunner.models.image_filter_value",
            "PipelineModel": "airunner.models.pipeline_model",
            "TargetFiles": "airunner.models.target_files",
            "FontSetting": "airunner.models.font_setting",
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
