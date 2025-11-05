"""Mixin providing list/collection properties for settings models."""

from typing import List, Type, Any, Optional

from airunner.components.application.gui.windows.main.settings_model_factory import (
    get_settings_model,
)
# Removed heavy import


class SettingsListPropertyMixin:
    """Provides @property access to model collections."""

    @property
    def chatbots(self) -> List[Type[Any]]:
        """Get all chatbot instances."""
        return self.load_chatbots()

    @property
    def ai_models(self) -> List[Type[Any]]:
        """Get all AI model configurations."""
        return self.load_ai_models()

    @property
    def schedulers(self) -> List[Type[Any]]:
        """Get all available scheduler configurations."""
        return self.load_schedulers()

    @property
    def shortcut_keys(self) -> List[Type[Any]]:
        """Get all keyboard shortcut configurations."""
        return self.load_shortcut_keys()

    @property
    def prompt_templates(self) -> List[Type[Any]]:
        """Get all prompt template configurations."""
        return self.load_prompt_templates()

    @property
    def controlnet_models(self) -> List[Type[Any]]:
        """Get all ControlNet model configurations."""
        return self.load_controlnet_models()

    @property
    def saved_prompts(self) -> List[Type[Any]]:
        """Get all saved prompt configurations."""
        return self.load_saved_prompts()

    @property
    def font_settings(self) -> List[Type[Any]]:
        """Get all font configurations."""
        return self.load_font_settings()

    @property
    def pipelines(self) -> List[Type[Any]]:
        """Get all pipeline configurations."""
        return self.load_pipelines()

    @property
    def image_filter_values(self) -> Optional[List[Any]]:
        """Get all image filter value configurations."""
        ImageFilterValue = get_settings_model("ImageFilterValue")
        return ImageFilterValue.objects.all()

    @property
    def chatbot(self) -> Optional[Any]:
        """Get current active chatbot."""
        from airunner.components.llm.utils import get_chatbot

        return get_chatbot()

    @property
    def user(self) -> Any:
        """Get or create current user."""
        User = get_settings_model("User")
        user = User.objects.first()
        if user is None:
            user = User()
            user.username = "User"
            user.save()
            user = User.objects.first()
        return user
