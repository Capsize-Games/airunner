"""Cohesive settings controller with injected dependencies.

The old ``SettingsMixin`` was a 7+ deep inheritance chain whose members
shared state implicitly through the host object. This controller replaces
that chain with composition: one explicit class owns the shared context and
delegates to focused worker objects that each receive the controller
(and therefore the shared state) explicitly instead of reading it off an
arbitrary ``self``.
"""

from __future__ import annotations

import inspect
from typing import Any, Dict, List, Optional, Type

from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import QApplication

from airunner.components.application.gui.windows.main.mixins import (
    BasicSettingsUpdateMixin,
    ImagePropertyMixin,
    LayerSettingsMixin,
    LayerSettingsUpdateMixin,
    ModelManagementMixin,
    SettingsCacheMixin,
    SettingsListPropertyMixin,
    SettingsLoaderMixin,
    SettingsPropertyMixin,
    UtilityAndChatbotMixin,
)
from airunner.components.application.gui.windows.main.settings_mixin_shared_instance import (
    SettingsMixinSharedInstance,
)
from airunner.daemon_client.resource_store import GuiResourceStore
from airunner.enums import SignalCode
from airunner.utils.application.get_logger import get_logger
from airunner_common.settings import AIRUNNER_LOG_LEVEL


class _Missing:
    """Sentinel for missing collaborator attributes."""


_MISSING = _Missing()


class _BoundMixin:
    """Base injected into worker objects so they share controller state.

    Worker objects are instantiated once per controller and receive the
    controller explicitly. Attribute reads that the worker does not define
    itself are forwarded to the controller, which owns the shared state.
    """

    _FORWARDED_ATTRS = {"_selected_layer_ids", "_qsettings_cache"}

    def __init__(self, _controller: "SettingsController") -> None:
        object.__setattr__(self, "_controller", _controller)

    def __getattr__(self, name: str) -> Any:
        controller = object.__getattribute__(self, "_controller")
        return getattr(controller, name)

    def __setattr__(self, name: str, value: Any) -> None:
        if name in self._FORWARDED_ATTRS:
            controller = object.__getattribute__(self, "_controller")
            object.__setattr__(controller, name, value)
            return
        object.__setattr__(self, name, value)


class SettingsController:
    """Explicit, cohesive settings facade shared by windows and workers.

    Parameters are injected explicitly (``owner``, ``api``, ``logger``) so
    consumers no longer depend on a sprawling inheritance chain. The focused
    worker objects below are plain, independently-instantiable collaborators
    rather than base classes.
    """

    _WORKER_CLASSES: tuple[Type[Any], ...] = (
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

    def __init__(
        self,
        owner: Any,
        api: Any = None,
        logger: Any = None,
    ) -> None:
        self._owner = owner
        self._api = api
        self._logger = logger
        self._resource_store: Any = None
        self._subs: list[Any] = [
            self._bind_worker(cls) for cls in self._WORKER_CLASSES
        ]
        self._selected_layer_ids: set[int] = set()
        self._qsettings_cache: Any = None
        self._register_layer_selection_handler()

    def _bind_worker(self, cls: Type[Any]) -> Any:
        """Return one controller-bound worker instance for ``cls``."""
        if not issubclass(cls, _BoundMixin):
            cls = type(cls.__name__, (cls, _BoundMixin), {})
        return cls(_controller=self)

    def __getattr__(self, name: str) -> Any:
        subs = self.__dict__.get("_subs")
        if not subs:
            raise AttributeError(name)
        for sub in subs:
            value = self._class_lookup(sub, name)
            if value is not _MISSING:
                return value
        raise AttributeError(name)

    @staticmethod
    def _class_lookup(sub: Any, name: str) -> Any:
        """Look ``name`` up on ``sub``'s class hierarchy only.

        This deliberately bypasses the instance ``__getattr__`` of the bound
        mixin (which forwards back to the controller) so attribute resolution
        cannot recurse between the controller and its collaborators.
        """
        for klass in type(sub).__mro__:
            if name not in klass.__dict__:
                continue
            attr = klass.__dict__[name]
            getter = getattr(attr, "__get__", None)
            if getter is not None:
                return getter(sub, type(sub))
            return attr
        return _MISSING

    def _owner_attr(self, name: str, default: Any = None) -> Any:
        """Read one attribute from the owner without triggering ``__getattr__``."""
        return self._owner.__dict__.get(name, default)

    @property
    def logger(self) -> Any:
        if self._logger is not None:
            return self._logger
        owner_logger = self._owner_attr("logger")
        if owner_logger is not None:
            return owner_logger
        return get_logger("AI Runner", AIRUNNER_LOG_LEVEL)

    @property
    def api(self) -> Any:
        if self._api is not None:
            return self._api
        owner_api = self._owner_attr("api")
        if owner_api is not None:
            return owner_api
        return self._resolve_api_reference()

    def _daemon_client(self) -> Any:
        daemon_client = self._owner_attr("daemon_client")
        if daemon_client is not None:
            return daemon_client
        api = self.refresh_api_reference()
        return getattr(api, "daemon_client", None)

    @property
    def settings_mixin_shared_instance(self) -> SettingsMixinSharedInstance:
        """Return the shared settings singleton."""
        return SettingsMixinSharedInstance()

    @property
    def resource_store(self) -> GuiResourceStore:
        """Return the shared daemon-backed resource store."""
        shared = self.settings_mixin_shared_instance
        daemon_client = self._daemon_client()

        if shared.resource_store is None:
            shared.resource_store = GuiResourceStore(daemon_client)
        elif (
            daemon_client is not None
            and getattr(shared.resource_store, "_daemon_client", None)
            is not daemon_client
        ):
            shared.resource_store = GuiResourceStore(daemon_client)
        return shared.resource_store

    @property
    def cached_send_image_to_canvas(self) -> List[Dict]:
        return self.settings_mixin_shared_instance.cached_send_image_to_canvas

    @cached_send_image_to_canvas.setter
    def cached_send_image_to_canvas(self, value: List[Dict]) -> None:
        self.settings_mixin_shared_instance.cached_send_image_to_canvas = value

    def _register_layer_selection_handler(self) -> None:
        """Register layer selection handling on the owner's signal table."""
        handlers = getattr(self._owner, "signal_handlers", None)
        if handlers is not None:
            handlers[SignalCode.LAYER_SELECTION_CHANGED] = (
                self._on_layer_selection_changed
            )
            return
        self._owner.signal_handlers = {
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
        current_api = self.api
        live_client = getattr(live_api, "daemon_client", None)
        current_client = getattr(current_api, "daemon_client", None)
        if live_client is not None and live_client is not current_client:
            self._api = live_api
        elif self._api_capability_score(live_api) > (
            self._api_capability_score(current_api)
        ):
            self._api = live_api
        elif current_api is None:
            self._api = live_api
        return self._api

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

    def _notify_setting_updated(
        self,
        setting_name: Optional[str] = None,
        column_name: Optional[str] = None,
        val: Any = None,
    ) -> None:
        """Notify that a setting was updated."""
        self._update_settings_cache(setting_name, column_name, val)
        self._notify_api_or_app(setting_name, column_name, val)

    def _update_settings_cache(
        self,
        setting_name: Optional[str],
        column_name: Optional[str],
        val: Any,
    ) -> None:
        """Update the settings cache from one setting change."""
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
        """Notify the API or application of a setting change."""
        api_ref = self.api
        if api_ref is not None:
            notify = getattr(api_ref, "application_settings_changed", None)
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

        notify = getattr(self._owner, "application_settings_changed", None)
        if callable(notify):
            notify(
                setting_name=setting_name,
                column_name=column_name,
                val=val,
            )
