"""Settings mixin providing unified access to all application settings.

This module composes multiple focused mixins to provide a clean interface
for settings management without a monolithic class.
"""

import inspect
from typing import List, Dict, Optional, Any
from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import QApplication
from airunner.enums import SignalCode
from airunner.daemon_client.resource_store import GuiResourceStore
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

        self._selected_layer_ids = set()
        self._register_layer_selection_handler()
        self.api = self._resolve_api_reference()

    def _register_layer_selection_handler(self) -> None:
        """Register layer selection handling on one settings-aware object."""
        if hasattr(self, "signal_handlers") and self.signal_handlers is not None:
            self.signal_handlers[SignalCode.LAYER_SELECTION_CHANGED] = (
                self._on_layer_selection_changed
            )
            return
        self.signal_handlers = {
            SignalCode.LAYER_SELECTION_CHANGED: (
                self._on_layer_selection_changed
            )
        }

    def _resolve_api_reference(self) -> Any:
        """Return the active app API without auto-creating a GUI singleton."""
        qt_api = self._api_from_qt_application()
        global_api = self._peek_global_api()
        if self._api_capability_score(global_api) > (
            self._api_capability_score(qt_api)
        ):
            return global_api
        if qt_api is not None:
            return qt_api
        return global_api

    @staticmethod
    def _api_capability_score(api: Any) -> int:
        """Score how complete one API reference is for worker usage."""
        if api is None:
            return -1
        attrs = ("daemon_client", "sounddevice_manager", "stt", "tts")
        return sum(
            1
            for attr in attrs
            if inspect.getattr_static(api, attr, None) is not None
        )

    def refresh_api_reference(self) -> Any:
        """Refresh one stale cached API reference when a better one exists."""
        live_api = self._resolve_api_reference()
        current_api = getattr(self, "api", None)
        live_client = getattr(live_api, "daemon_client", None)
        current_client = getattr(current_api, "daemon_client", None)
        if live_client is not None and live_client is not current_client:
            self.api = live_api
        elif self._api_capability_score(live_api) > (
            self._api_capability_score(current_api)
        ):
            self.api = live_api
        elif current_api is None:
            self.api = live_api
        return getattr(self, "api", None)

    @staticmethod
    def _api_from_qt_application() -> Any:
        """Return the API attached to the running Qt application, if any."""
        app = QApplication.instance() or QCoreApplication.instance()
        if app is None:
            return None
        return getattr(app, "api", None)

    @staticmethod
    def _peek_global_api() -> Any:
        """Return None now that API lookup is app-scoped only."""
        return None

    @property
    def settings_mixin_shared_instance(self) -> SettingsMixinSharedInstance:
        """Get shared settings instance.

        Returns:
            SettingsMixinSharedInstance singleton.
        """
        return SettingsMixinSharedInstance()

    @property
    def resource_store(self) -> GuiResourceStore:
        """Return the shared daemon-backed resource store."""
        shared = self.settings_mixin_shared_instance
        daemon_client = getattr(self, "daemon_client", None)
        if daemon_client is None:
            api = self.refresh_api_reference()
            daemon_client = getattr(api, "daemon_client", None)

        if shared.resource_store is None:
            shared.resource_store = GuiResourceStore(daemon_client)
        elif (
            daemon_client is not None
            and shared.resource_store._daemon_client is not daemon_client
        ):
            shared.resource_store = GuiResourceStore(daemon_client)
        return shared.resource_store

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
        api_ref = getattr(self, "api", None)
        if api_ref is not None:
            notify = getattr(
                api_ref,
                "application_settings_changed",
                None,
            )
            if callable(notify):
                notify(
                    setting_name=setting_name,
                    column_name=column_name,
                    val=val,
                )
                return

            emit_signal = getattr(api_ref, "emit_signal", None)
            if callable(emit_signal):
                emit_signal(
                    SignalCode.APPLICATION_SETTINGS_CHANGED_SIGNAL,
                    {
                        "setting_name": setting_name,
                        "column_name": column_name,
                        "val": val,
                    },
                )
                return

        notify = getattr(self, "application_settings_changed", None)
        if callable(notify):
            notify(
                setting_name=setting_name,
                column_name=column_name,
                val=val,
            )
