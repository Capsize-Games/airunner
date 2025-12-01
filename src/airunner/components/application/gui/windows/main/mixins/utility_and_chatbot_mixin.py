"""Mixin providing utility and chatbot management operations."""

import os
from typing import Optional
from airunner.components.data.session_manager import session_scope
from airunner.components.llm.data.chatbot import Chatbot
from airunner.components.llm.data.target_files import TargetFiles
from airunner.components.settings.data.path_settings import PathSettings
from airunner.components.settings.data.application_settings import (
    ApplicationSettings,
)
from airunner.components.art.data.active_grid_settings import (
    ActiveGridSettings,
)
from airunner.components.art.data.controlnet_settings import (
    ControlnetSettings,
)
from airunner.components.art.data.image_to_image_settings import (
    ImageToImageSettings,
)
from airunner.components.art.data.outpaint_settings import (
    OutpaintSettings,
)
from airunner.components.art.data.drawingpad_settings import (
    DrawingPadSettings,
)
from airunner.components.art.data.metadata_settings import (
    MetadataSettings,
)
from airunner.components.art.data.generator_settings import (
    GeneratorSettings,
)
from airunner.components.llm.data.llm_generator_settings import (
    LLMGeneratorSettings,
)
from airunner.components.tts.data.models.espeak_settings import EspeakSettings
from airunner.components.stt.data.stt_settings import STTSettings
from airunner.components.art.data.brush_settings import BrushSettings
from airunner.components.art.data.grid_settings import GridSettings
from airunner.components.art.data.memory_settings import MemorySettings
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

    @staticmethod
    def create_chatbot(chatbot_name: str) -> Chatbot:
        """Create a new chatbot or return existing one.

        Args:
            chatbot_name: Name of the chatbot.

        Returns:
            Chatbot instance.
        """
        existing = Chatbot.objects.filter_by_first(name=chatbot_name)
        if existing:
            return existing

        try:
            new_chatbot = Chatbot(name=chatbot_name)
            new_chatbot.save()
            return new_chatbot
        except Exception:
            return (
                Chatbot.objects.filter_by_first(name=chatbot_name)
                or Chatbot.objects.first()
                or Chatbot(name=chatbot_name, botname="Fallback")
            )

    @staticmethod
    def delete_chatbot_by_name(chatbot_name: str) -> None:
        """Delete chatbot by name.

        Args:
            chatbot_name: Name of the chatbot to delete.
        """
        Chatbot.objects.delete_by(name=chatbot_name)

    def get_chatbot_by_id(self, chatbot_id: int) -> Chatbot:
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

    @staticmethod
    def add_chatbot_document_to_chatbot(
        chatbot: Chatbot, file_path: str
    ) -> None:
        """Add a document file to a chatbot.

        Args:
            chatbot: Chatbot instance.
            file_path: Path to the document file.
        """
        document = TargetFiles.objects.filter_by_first(
            chatbot_id=chatbot.id, file_path=file_path
        )
        if document is None:
            document = TargetFiles(file_path=file_path, chatbot_id=chatbot.id)
        TargetFiles.objects.merge(document)

    @staticmethod
    def reset_settings() -> None:
        """Reset all settings to default values.

        Deletes all settings from database. They will be recreated
        with default values when accessed again.
        """
        settings_models = [
            ApplicationSettings,
            ActiveGridSettings,
            ControlnetSettings,
            ImageToImageSettings,
            OutpaintSettings,
            DrawingPadSettings,
            MetadataSettings,
            GeneratorSettings,
            LLMGeneratorSettings,
            EspeakSettings,
            STTSettings,
            BrushSettings,
            GridSettings,
            PathSettings,
            MemorySettings,
        ]

        for cls in settings_models:
            cls.objects.delete_all()

        # Clear cache
        try:
            SettingsMixinSharedInstance()._settings_cache.clear()
        except Exception:
            pass

    def reset_path_settings(self) -> None:
        """Reset path settings to defaults."""
        PathSettings.objects.delete_all()
        self.set_default_values(PathSettings)

    @staticmethod
    def set_default_values(model_name_) -> None:
        """Set default values for a model.

        Args:
            model_name_: Model class to set defaults for.
        """
        with session_scope() as session:
            default_values = {}
            for column in model_name_.__table__.columns:
                if column.default is not None:
                    default_values[column.name] = column.default.arg
            session.execute(model_name_.__table__.insert(), [default_values])
            session.commit()

    def _load_chatbot_with_relationships(
        self, chatbot_id: int
    ) -> Optional[Chatbot]:
        """Load chatbot with relationships.

        Args:
            chatbot_id: Chatbot ID.

        Returns:
            Chatbot instance or None.
        """
        try:
            chatbot = Chatbot.objects.get(
                pk=chatbot_id,
                eager_load=["target_files", "target_directories"],
            )
            return chatbot
        except Exception as e:
            self.logger.error(f"Error getting chatbot by id: {e}")
            return None
