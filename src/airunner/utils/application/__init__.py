import os

from airunner.utils.application.create_worker import create_worker
from airunner.utils.application.get_logger import get_logger
from airunner.utils.application.get_torch_device import get_torch_device
from airunner.utils.application.get_version import get_version
from airunner.utils.application.mediator_mixin import MediatorMixin
from airunner.utils.application.platform_info import (
    get_platform_name,
    is_linux,
    is_bsd,
    is_darwin,
    is_windows,
)
from airunner.utils.application.random_seed import random_seed
from airunner.utils.application.signal_mediator import SignalMediator

# Only import UI-related modules if not in headless mode
if not os.environ.get("AIRUNNER_HEADLESS"):
    from airunner.utils.application.set_widget_state import set_widget_state
    from airunner.utils.application.ui_loader import (
        load_ui_from_string,
    )


__all__ = [
    "create_worker",
    "get_logger",
    "get_torch_device",
    "get_version",
    "MediatorMixin",
    "SignalMediator",
    "get_platform_name",
    "is_linux",
    "is_bsd",
    "is_darwin",
    "is_windows",
    "random_seed",
]

# Add UI exports only if not headless
if not os.environ.get("AIRUNNER_HEADLESS"):
    __all__.extend(["set_widget_state", "load_ui_from_string"])
