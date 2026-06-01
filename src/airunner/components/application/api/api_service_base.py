"""Base API service class for all API services."""
from typing import Any, Optional

from PySide6.QtCore import QCoreApplication, QObject

from airunner.utils.application.mediator_mixin import MediatorMixin
from airunner.utils.application.get_logger import get_logger


class APIServiceBase(MediatorMixin, QObject):
    """Base class for all API services.

    Provides signal-based communication via MediatorMixin and delegates
    settings/image helper access to the live API singleton.
    """

    def __init__(self, api: Optional[Any] = None):
        super().__init__()
        self.logger = get_logger(self.__class__.__module__)
        self.api = api or self._resolve_api_reference()

    @staticmethod
    def _resolve_api_reference() -> Optional[Any]:
        qt_app = QCoreApplication.instance()
        if qt_app is not None:
            return getattr(qt_app, "api", None)
        return None

    def __getattr__(self, name: str) -> Any:
        api = self._resolve_api_reference()
        if api is not None and hasattr(api, name):
            self.api = api
            return getattr(api, name)
        raise AttributeError(
            f"{self.__class__.__name__!s} has no attribute {name!r}"
        )
