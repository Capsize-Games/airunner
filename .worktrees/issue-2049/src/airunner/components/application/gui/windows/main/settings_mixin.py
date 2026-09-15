"""Backward-compatible settings mixin backed by :class:`SettingsController`.

The old implementation was a 7+ deep inheritance chain whose members shared
state implicitly through the host object. It now delegates to the cohesive
``SettingsController``, which uses explicit composition and injected
dependencies. The mixin itself remains only as a thin compatibility shim for
the large number of widgets/workers that still subclass it.
"""

from __future__ import annotations

from typing import Any

from airunner.components.application.gui.windows.main.settings_controller import (
    SettingsController,
)


class SettingsMixin:
    """Thin delegation shim over the explicit settings controller.

    Attributes are resolved through ``self._settings_controller``, which
    owns all settings behavior. Subclasses keep working unchanged while the
    implementation lives in one cohesive class.
    """

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._settings_controller = SettingsController(
            owner=self,
            api=getattr(self, "api", None),
            logger=getattr(self, "logger", None),
        )

    def __getattr__(self, name: str) -> Any:
        controller = self.__dict__.get("_settings_controller")
        if controller is None:
            raise AttributeError(name)
        return getattr(controller, name)

    def __setattr__(self, name: str, value: Any) -> None:
        if name.startswith("_settings_controller"):
            super().__setattr__(name, value)
            return
        super().__setattr__(name, value)

    @property
    def settings_controller(self) -> SettingsController:
        """Return the injected settings controller."""
        return self.__dict__.get("_settings_controller")
