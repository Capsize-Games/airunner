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
            "STTSettings": "airunner_model.models.stt_settings",
            "ApplicationSettings": "airunner_model.models.application_settings",
            "LanguageSettings": "airunner_model.models.language_settings",
            "SoundSettings": "airunner_model.models.sound_settings",
            "WhisperSettings": "airunner_model.models.whisper_settings",
            "WindowSettings": "airunner_model.models.window_settings",
            "RAGSettings": "airunner_model.models.rag_settings",
            "LLMGeneratorSettings": "airunner_model.models.llm_generator_settings",
            "GeneratorSettings": "airunner_model.models.generator_settings",
            "ControlnetSettings": "airunner_model.models.controlnet_settings",
            "ImageToImageSettings": "airunner_model.models.image_to_image_settings",
            "OutpaintSettings": "airunner_model.models.outpaint_settings",
            "DrawingPadSettings": "airunner_model.models.drawingpad_settings",
            "BrushSettings": "airunner_model.models.brush_settings",
            "MetadataSettings": "airunner_model.models.metadata_settings",
            "GridSettings": "airunner_model.models.grid_settings",
            "ActiveGridSettings": "airunner_model.models.active_grid_settings",
            "PathSettings": "airunner_model.models.path_settings",
            "MemorySettings": "airunner_model.models.memory_settings",
            "VoiceSettings": "airunner_model.models.voice_settings",
            "EspeakSettings": "airunner_model.models.espeak_settings",
            "OpenVoiceSettings": "airunner_model.models.openvoice_settings",
            "Chatbot": "airunner_model.models.chatbot",
            "CanvasLayer": "airunner_model.models.canvas_layer",
            "AIModels": "airunner_model.models.ai_models",
            "Schedulers": "airunner_model.models.schedulers",
            "User": "airunner_model.models.user",
            "Embedding": "airunner_model.models.embedding",
            "Lora": "airunner_model.models.lora",
            "SavedPrompt": "airunner_model.models.saved_prompt",
            "PromptTemplate": "airunner_model.models.prompt_template",
            "ControlnetModel": "airunner_model.models.controlnet_model",
            "ImageFilterValue": "airunner_model.models.image_filter_value",
            "PipelineModel": "airunner_model.models.pipeline_model",
            "TargetFiles": "airunner_model.models.target_files",
            "FontSetting": "airunner_model.models.font_setting",
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
