"""Mixin providing list and collection properties for GUI resources."""

from typing import Any, List, Optional


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
        return self.resource_store.query("ImageFilterValue")

    @property
    def chatbot(self) -> Optional[Any]:
        """Get current active chatbot."""
        cached = self.settings_mixin_shared_instance.chatbot
        if cached is not None:
            return cached
        chatbot = self.resource_store.first(
            "Chatbot",
            filters={"current": True},
            eager_load=["target_files", "target_directories"],
        )
        if chatbot is None:
            chatbot = self.resource_store.first(
                "Chatbot",
                eager_load=["target_files", "target_directories"],
            )
        if chatbot is None:
            chatbot = self.resource_store.create(
                "Chatbot",
                {"name": "Default", "botname": "Computer", "current": True},
            )
        self.settings_mixin_shared_instance.chatbot = chatbot
        return chatbot

    @property
    def user(self) -> Any:
        """Get or create current user."""
        user = self.resource_store.first("User")
        if user is None:
            user = self.resource_store.create("User", {"username": "User"})
        return user
