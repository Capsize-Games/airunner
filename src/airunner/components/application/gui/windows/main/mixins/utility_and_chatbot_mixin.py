"""Mixin providing utility and chatbot management operations."""

import os
from typing import Any, Optional

from airunner.components.application.gui.windows.main.settings_mixin_shared_instance import (
    SettingsMixinSharedInstance,
)


class UtilityAndChatbotMixin:
    """Mixin for utility functions and chatbot management."""

    @property
    def user_web_dir(self) -> str:
        """Return the user code directory.

        Returns:
            Path to user's web/code directory.
        """
        return os.path.join(
            os.path.expanduser(self.path_settings.base_path), "code"
        )

    def create_chatbot(self, chatbot_name: str) -> Any:
        """Create a new chatbot or return existing one.

        Args:
            chatbot_name: Name of the chatbot.

        Returns:
            Chatbot instance.
        """
        existing = self.resource_store.first(
            "Chatbot",
            filters={"name": chatbot_name},
        )
        if existing:
            return existing

        try:
            return self.resource_store.create(
                "Chatbot",
                {"name": chatbot_name, "botname": "Computer"},
            )
        except Exception:
            return (
                self.resource_store.first("Chatbot", filters={"name": chatbot_name})
                or self.resource_store.first("Chatbot")
                or self.resource_store.new_record(
                    "Chatbot",
                    {"name": chatbot_name, "botname": "Fallback"},
                )
            )

    def delete_chatbot_by_name(self, chatbot_name: str) -> None:
        """Delete chatbot by name.

        Args:
            chatbot_name: Name of the chatbot to delete.
        """
        chatbots = self.resource_store.query(
            "Chatbot",
            filters={"name": chatbot_name},
        )
        for chatbot in chatbots:
            self.resource_store.delete("Chatbot", chatbot.id)

    def get_chatbot_by_id(self, chatbot_id: int) -> Any:
        """Get chatbot by ID with eager loading.

        Args:
            chatbot_id: ID of the chatbot.

        Returns:
            Chatbot instance.
        """
        if not self.settings_mixin_shared_instance.chatbot:
            chatbot = self._load_chatbot_with_relationships(chatbot_id)
            if chatbot is None:
                chatbot = self.create_chatbot("Default")
            self.settings_mixin_shared_instance.chatbot = chatbot

        return self.settings_mixin_shared_instance.chatbot

    def add_chatbot_document_to_chatbot(
        self,
        chatbot: Any,
        file_path: str,
    ) -> None:
        """Add a document file to a chatbot.

        Args:
            chatbot: Chatbot instance.
            file_path: Path to the document file.
        """
        document = self.resource_store.first(
            "TargetFiles",
            filters={"chatbot_id": chatbot.id, "file_path": file_path},
        )
        if document is None:
            self.resource_store.create(
                "TargetFiles",
                {"file_path": file_path, "chatbot_id": chatbot.id},
            )

    def reset_settings(self) -> None:
        """Reset all settings to default values.

        Deletes all settings from database. They will be recreated
        with default values when accessed again.
        """
        settings_resources = [
            "ApplicationSettings",
            "ActiveGridSettings",
            "ControlnetSettings",
            "ImageToImageSettings",
            "OutpaintSettings",
            "DrawingPadSettings",
            "MetadataSettings",
            "GeneratorSettings",
            "LLMGeneratorSettings",
            "EspeakSettings",
            "STTSettings",
            "BrushSettings",
            "GridSettings",
            "PathSettings",
            "MemorySettings",
        ]

        for resource_name in settings_resources:
            if self.resource_store.is_singleton(resource_name):
                record = self.resource_store.get_singleton(resource_name)
                if getattr(record, "id", None) is not None:
                    self.resource_store.delete(resource_name, record.id)
                continue
            self.resource_store.delete_many(resource_name)

        # Clear cache
        try:
            SettingsMixinSharedInstance()._settings_cache.clear()
        except Exception:
            pass

    def reset_path_settings(self) -> None:
        """Reset path settings to defaults."""
        self.resource_store.delete_many("PathSettings")
        self.set_default_values("PathSettings")

    def set_default_values(self, resource_name: str) -> None:
        """Set default values for a model.

        Args:
            resource_name: Resource name to set defaults for.
        """
        if self.resource_store.is_singleton(resource_name):
            self.resource_store.get_singleton(resource_name, create_if_missing=True)
            return
        self.resource_store.create(resource_name, {})

    def _load_chatbot_with_relationships(
        self, chatbot_id: int
    ) -> Optional[Any]:
        """Load chatbot with relationships.

        Args:
            chatbot_id: Chatbot ID.

        Returns:
            Chatbot instance or None.
        """
        try:
            chatbot = self.resource_store.first(
                "Chatbot",
                filters={"id": chatbot_id},
                eager_load=["target_files", "target_directories"],
            )
            return chatbot
        except Exception as e:
            self.logger.error(f"Error getting chatbot by id: {e}")
            return None
