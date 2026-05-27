"""Mixin providing database loading operations for settings models."""

from typing import Type, Any, Optional, List

from airunner.components.application.gui.windows.main.settings_model_factory import (
    get_settings_model,
)
from airunner.utils.application.get_logger import get_logger
from airunner.settings import AIRUNNER_LOG_LEVEL


class SettingsLoaderMixin:
    """Provides static methods for loading settings and models from database."""

    @staticmethod
    def load_schedulers() -> List[Any]:
        """Load all scheduler configurations.

        Returns:
            List of Schedulers instances.
        """
        Schedulers = get_settings_model("Schedulers")
        return Schedulers.objects.all()

    @staticmethod
    def load_ai_models() -> List[Any]:
        """Load all AI model configurations.

        Returns:
            List of AIModels instances.
        """
        AIModels = get_settings_model("AIModels")
        return AIModels.objects.all()

    @staticmethod
    def load_chatbots() -> List[Any]:
        """Load all chatbot instances.

        Returns:
            List of Chatbot instances.
        """
        Chatbot = get_settings_model("Chatbot")
        return Chatbot.objects.all()

    @staticmethod
    def load_saved_prompts() -> List[Any]:
        """Load all saved prompt configurations.

        Returns:
            List of SavedPrompt instances.
        """
        SavedPrompt = get_settings_model("SavedPrompt")
        return SavedPrompt.objects.all()

    @staticmethod
    def load_font_settings() -> List[Any]:
        """Load all font configurations.

        Returns:
            List of FontSetting instances.
        """
        FontSetting = get_settings_model("FontSetting")
        return FontSetting.objects.all()

    @staticmethod
    def load_prompt_templates() -> List[Any]:
        """Load all prompt template configurations.

        Returns:
            List of PromptTemplate instances.
        """
        PromptTemplate = get_settings_model("PromptTemplate")
        return PromptTemplate.objects.all()

    @staticmethod
    def load_controlnet_models() -> List[Any]:
        """Load all ControlNet model configurations.

        Returns:
            List of ControlnetModel instances.
        """
        ControlnetModel = get_settings_model("ControlnetModel")
        return ControlnetModel.objects.all()

    @staticmethod
    def load_pipelines() -> List[Any]:
        """Load all pipeline configurations.

        Returns:
            List of PipelineModel instances.
        """
        PipelineModel = get_settings_model("PipelineModel")
        return PipelineModel.objects.all()

    @staticmethod
    def load_shortcut_keys() -> List[Any]:
        """Load all keyboard shortcut configurations.

        Returns:
            List of ShortcutKeys instances.
        """
        from airunner.components.application.data import ShortcutKeys

        return ShortcutKeys.objects.all()

    @staticmethod
    def load_lora() -> List[Any]:
        """Load all LoRA configurations.

        Returns:
            List of Lora instances.
        """
        Lora = get_settings_model("Lora")
        return Lora.objects.all()

    @staticmethod
    def load_settings_from_db(
        model_class_: Type[Any], eager_load: Optional[List[str]] = None
    ) -> Any:
        """Load settings through the daemon-backed model manager.

        Args:
            model_class_: SQLAlchemy model class for the settings table.
            eager_load: Optional list of relationship names to eager-load.

        Returns:
            Instance of the settings model.
        """
        try:
            settings_instance = model_class_.objects.first(
                eager_load=eager_load,
            )
            if settings_instance is None:
                settings_instance = model_class_.objects.create()
                if settings_instance is None:
                    settings_instance = model_class_()
                elif eager_load:
                    settings_instance = model_class_.objects.first(
                        eager_load=eager_load,
                    ) or settings_instance
            return settings_instance
        except Exception as e:
            return SettingsLoaderMixin._handle_load_error(e, model_class_)

    @staticmethod
    def _handle_load_error(error: Exception, model_class_: Type[Any]) -> Any:
        """Handle error during settings loading.

        Args:
            error: Exception that occurred.
            model_class_: Model class that failed to load.

        Returns:
            Fallback default instance.

        Raises:
            RuntimeError: If even fallback instance creation fails.
        """
        logger = get_logger("AI Runner SettingsMixin", AIRUNNER_LOG_LEVEL)
        logger.error(
            f"Error loading settings for {model_class_.__name__}: {error}. "
            "Attempting to return a new transient default instance.",
            exc_info=True,
        )

        try:
            return model_class_()
        except Exception as e_fallback:
            logger.critical(
                f"CRITICAL: Failed to create fallback instance for "
                f"{model_class_.__name__} during error handling. "
                f"Fallback error: {e_fallback}",
                exc_info=True,
            )
            raise RuntimeError(
                f"Fatal error in settings: Could not instantiate default "
                f"for {model_class_.__name__} after initial load failed. "
                f"Original error: {error}"
            ) from e_fallback
