# This module contains the base API service class for all API services.
import os

from airunner.utils.application.mediator_mixin import MediatorMixin

# Conditionally import Qt and SettingsMixin only if not in headless mode
_HEADLESS = os.environ.get("AIRUNNER_HEADLESS", "").lower() in ("1", "true", "yes")

if not _HEADLESS:
    from airunner.components.application.gui.windows.main.settings_mixin import (
        SettingsMixin,
    )
    from PySide6.QtCore import QObject

    class APIServiceBase(MediatorMixin, SettingsMixin, QObject):
        """Base class for all API services.

        Provides signal-based communication via MediatorMixin and
        settings access via SettingsMixin.
        """

        def __init__(self):
            super().__init__()
else:
    # Headless mode: no Qt dependencies
    class APIServiceBase(MediatorMixin):
        """Base class for all API services (headless mode).

        Provides signal-based communication via MediatorMixin.
        No Qt dependencies in headless mode.
        """

        def __init__(self):
            super().__init__()
