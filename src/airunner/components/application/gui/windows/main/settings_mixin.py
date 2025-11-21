"""Settings mixin providing unified access to all application settings.

This module composes multiple focused mixins to provide a clean interface
for settings management without a monolithic class.
"""

from typing import List, Dict, Optional, Any
from PySide6.QtWidgets import QApplication
from airunner.enums import SignalCode
from airunner.utils.application.get_logger import get_logger
from airunner.settings import AIRUNNER_LOG_LEVEL
from airunner.components.application.gui.windows.main.settings_mixin_shared_instance import (
    SettingsMixinSharedInstance,
)
from airunner.components.application.gui.windows.main.mixins import (
    SettingsPropertyMixin,
    SettingsListPropertyMixin,
    ImagePropertyMixin,
    SettingsCacheMixin,
    LayerSettingsMixin,
    SettingsLoaderMixin,
    BasicSettingsUpdateMixin,
    LayerSettingsUpdateMixin,
    ModelManagementMixin,
    UtilityAndChatbotMixin,
)


class SettingsMixin(
    SettingsPropertyMixin,
    SettingsListPropertyMixin,
    ImagePropertyMixin,
    SettingsCacheMixin,
    LayerSettingsMixin,
    SettingsLoaderMixin,
    BasicSettingsUpdateMixin,
    LayerSettingsUpdateMixin,
    ModelManagementMixin,
    UtilityAndChatbotMixin,
):
    """Unified settings management mixin.

    Composes 10 focused mixins to provide settings access and management:
    - SettingsPropertyMixin: Individual settings properties
    - SettingsListPropertyMixin: Collection properties
    - ImagePropertyMixin: Image and layer composition
    - SettingsCacheMixin: Cache management
    - LayerSettingsMixin: Layer-specific settings
    - SettingsLoaderMixin: Database loading operations
    - BasicSettingsUpdateMixin: Non-layer settings updates
    - LayerSettingsUpdateMixin: Layer-specific updates
    - ModelManagementMixin: AI models, LoRA, embeddings
    - UtilityAndChatbotMixin: Utility functions and chatbots
    """

    def __init__(self, *args, **kwargs):
        """Initialize settings mixin with layer tracking."""
        self.logger = get_logger("AI Runner", AIRUNNER_LOG_LEVEL)

        super().__init__(*args, **kwargs)

        # Initialize layer selection tracking
        self._selected_layer_ids = set()

        # Add layer selection signal handler
        if (
            hasattr(self, "signal_handlers")
            and self.signal_handlers is not None
        ):
            self.signal_handlers[SignalCode.LAYER_SELECTION_CHANGED] = (
                self._on_layer_selection_changed
            )
        else:
            self.signal_handlers = {
                SignalCode.LAYER_SELECTION_CHANGED: (
                    self._on_layer_selection_changed
                )
            }


        # Get API reference from application
        app = QApplication.instance()
        if app:
            self.api = getattr(app, "api", None)
        else:
            # In headless mode, there's no QApplication, so get API from global instance
            try:
                from airunner.components.server.api.server import get_api
                self.api = get_api()
            except Exception as e:
                self.api = None

    @property
    def settings_mixin_shared_instance(self) -> SettingsMixinSharedInstance:
        """Get shared settings instance.

        Returns:
            SettingsMixinSharedInstance singleton.
        """
        return SettingsMixinSharedInstance()

    @property
    def cached_send_image_to_canvas(self) -> List[Dict]:
        """Get cached send image to canvas data.

        Returns:
            List of cached image data.
        """
        return self.settings_mixin_shared_instance.cached_send_image_to_canvas

    @cached_send_image_to_canvas.setter
    def cached_send_image_to_canvas(self, value: List[Dict]) -> None:
        """Set cached send image to canvas data.

        Args:
            value: List of cached image data.
        """
        self.settings_mixin_shared_instance.cached_send_image_to_canvas = value

    def _notify_setting_updated(
        self,
        setting_name: Optional[str] = None,
        column_name: Optional[str] = None,
        val: Any = None,
    ) -> None:
        """Notify that a setting was updated.

        This method is called by mixins to propagate setting changes.

        Args:
            setting_name: Database table name.
            column_name: Column name.
            val: New value.
        """
        self._update_settings_cache(setting_name, column_name, val)
        self._notify_api_or_app(setting_name, column_name, val)

    def _update_settings_cache(
        self,
        setting_name: Optional[str],
        column_name: Optional[str],
        val: Any,
    ) -> None:
        """Update settings cache.

        Args:
            setting_name: Database table name.
            column_name: Column name.
            val: New value.
        """
        try:
            self.settings_mixin_shared_instance.on_settings_updated(
                setting_name, column_name, val
            )
        except Exception as e:
            self.logger.error(
                f"Error updating settings cache in "
                f"SettingsMixinSharedInstance: {e}"
            )

    def _notify_api_or_app(
        self,
        setting_name: Optional[str],
        column_name: Optional[str],
        val: Any,
    ) -> None:
        """Notify API or application of setting change.

        Args:
            setting_name: Database table name.
            column_name: Column name.
            val: New value.
        """
        if hasattr(self, "api") and self.api:
            self.api.application_settings_changed(
                setting_name=setting_name,
                column_name=column_name,
                val=val,
            )
        elif hasattr(self, "application_settings_changed"):
            self.application_settings_changed(
                setting_name=setting_name,
                column_name=column_name,
                val=val,
            )
