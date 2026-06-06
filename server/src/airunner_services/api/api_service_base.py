"""Service-owned base class for shared API service facades."""

from airunner_services.utils.application.get_logger import get_logger
from airunner_services.utils.application.mediator_mixin import MediatorMixin
from airunner_services.utils.application.runtime_primitives import QObject
from airunner_services.utils.application.runtime_context_mixin import (
    RuntimeContextMixin,
)


class APIServiceBase(RuntimeContextMixin, MediatorMixin, QObject):
    """Base class for shared API services without direct Qt dependencies."""

    def __init__(self) -> None:
        super().__init__()
        self.logger = get_logger(self.__class__.__module__)
