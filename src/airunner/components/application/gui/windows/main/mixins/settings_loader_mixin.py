"""Mixin providing daemon-backed loading operations for GUI resources."""

from typing import Any, Optional, List

from airunner.utils.application.get_logger import get_logger
from airunner.settings import AIRUNNER_LOG_LEVEL


class SettingsLoaderMixin:
    """Provides static methods for loading settings and models from database."""

    def load_schedulers(self) -> List[Any]:
        """Load all scheduler configurations.

        Returns:
            List of Schedulers instances.
        """
        return self.resource_store.query("Schedulers")

    def load_ai_models(self) -> List[Any]:
        """Load all AI model configurations.

        Returns:
            List of AIModels instances.
        """
        return self.resource_store.query("AIModels")

    def load_chatbots(self) -> List[Any]:
        """Load all chatbot instances.

        Returns:
            List of Chatbot instances.
        """
        return self.resource_store.query("Chatbot")

    def load_saved_prompts(self) -> List[Any]:
        """Load all saved prompt configurations.

        Returns:
            List of SavedPrompt instances.
        """
        return self.resource_store.query("SavedPrompt")

    def load_font_settings(self) -> List[Any]:
        """Load all font configurations.

        Returns:
            List of FontSetting instances.
        """
        return self.resource_store.query("FontSetting")

    def load_prompt_templates(self) -> List[Any]:
        """Load all prompt template configurations.

        Returns:
            List of PromptTemplate instances.
        """
        return self.resource_store.query("PromptTemplate")

    def load_controlnet_models(self) -> List[Any]:
        """Load all ControlNet model configurations.

        Returns:
            List of ControlnetModel instances.
        """
        return self.resource_store.query("ControlnetModel")

    def load_pipelines(self) -> List[Any]:
        """Load all pipeline configurations.

        Returns:
            List of PipelineModel instances.
        """
        return self.resource_store.query("PipelineModel")

    def load_shortcut_keys(self) -> List[Any]:
        """Load all keyboard shortcut configurations.

        Returns:
            List of ShortcutKeys instances.
        """
        return self.resource_store.query("ShortcutKeys")

    def load_lora(self) -> List[Any]:
        """Load all LoRA configurations.

        Returns:
            List of Lora instances.
        """
        return self.resource_store.query("Lora")

    def load_settings_from_db(
        self,
        resource_name: str,
        eager_load: Optional[List[str]] = None,
    ) -> Any:
        """Load settings through the daemon-backed model manager.

        Args:
            resource_name: Resource name for the settings row.
            eager_load: Optional list of relationship names to eager-load.

        Returns:
            Instance of the settings model.
        """
        try:
            if self.resource_store.is_singleton(resource_name):
                settings_instance = self.resource_store.get_singleton(
                    resource_name,
                    create_if_missing=True,
                )
            else:
                settings_instance = self.resource_store.first(
                    resource_name,
                    eager_load=eager_load,
                )
                if settings_instance is None:
                    settings_instance = self.resource_store.create(
                        resource_name,
                        {},
                    )
            return settings_instance
        except Exception as e:
            return self._handle_load_error(e, resource_name)

    @staticmethod
    def _handle_load_error(error: Exception, resource_name: str) -> Any:
        """Handle error during settings loading.

        Args:
            error: Exception that occurred.
            resource_name: Resource that failed to load.

        Returns:
            Fallback default instance.

        Raises:
            RuntimeError: If even fallback instance creation fails.
        """
        logger = get_logger("AI Runner SettingsMixin", AIRUNNER_LOG_LEVEL)
        logger.error(
            f"Error loading settings for {resource_name}: {error}. "
            "Attempting to return a new transient default instance.",
            exc_info=True,
        )

        return {"resource_name": resource_name, "error": str(error)}
