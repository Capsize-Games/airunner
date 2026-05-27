"""Service-owned application utilities used by headless and shared code."""

from airunner_services.utils.application.api_reference import (
    api_from_qt_application,
)
from airunner_services.utils.application.api_reference import (
    peek_registered_api,
)
from airunner_services.utils.application.api_reference import (
    resolve_live_api_reference,
)
from airunner_services.utils.application.create_worker import create_worker
from airunner_services.utils.application.enum_resolver import (
    handler_state_type,
)
from airunner_services.utils.application.enum_resolver import llm_action_type
from airunner_services.utils.application.enum_resolver import (
    model_action_type,
)
from airunner_services.utils.application.enum_resolver import (
    signal_code_member,
)
from airunner_services.utils.application.enum_resolver import signal_code_proxy
from airunner_services.utils.application.get_logger import get_logger
from airunner_services.utils.application.get_torch_device import (
    get_torch_device,
)
from airunner_services.utils.application.get_version import get_version
from airunner_services.utils.application.mediator_mixin import (
    MediatorMixin,
)
from airunner_services.utils.application.platform_info import (
    get_platform_name,
)
from airunner_services.utils.application.platform_info import is_bsd
from airunner_services.utils.application.platform_info import is_darwin
from airunner_services.utils.application.platform_info import is_linux
from airunner_services.utils.application.platform_info import is_windows
from airunner_services.utils.application.random_seed import random_seed
from airunner_services.utils.application.signal_mediator import (
    SignalMediator,
)


__all__ = [
    "api_from_qt_application",
    "create_worker",
    "handler_state_type",
    "get_logger",
    "get_platform_name",
    "get_torch_device",
    "get_version",
    "is_bsd",
    "is_darwin",
    "is_linux",
    "is_windows",
    "llm_action_type",
    "MediatorMixin",
    "model_action_type",
    "peek_registered_api",
    "random_seed",
    "resolve_live_api_reference",
    "RuntimeContextMixin",
    "signal_code_member",
    "signal_code_proxy",
    "SignalMediator",
]


def __getattr__(name: str):
    """Resolve cycle-prone application exports lazily."""
    if name == "RuntimeContextMixin":
        from airunner_services.utils.application.runtime_context_mixin import (
            RuntimeContextMixin,
        )

        return RuntimeContextMixin
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
