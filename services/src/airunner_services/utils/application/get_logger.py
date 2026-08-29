"""Service-owned re-export of the shared AIRunner logger factory.

The canonical implementation lives in :mod:`airunner_common.get_logger`
(issue #2050). This module is a thin shim that also registers the
services-specific ``PathSettings``-based log base path resolver so file
logging continues to honour the user-configured ``base_path``.
"""

from __future__ import annotations

from typing import Optional

from airunner_common.get_logger import Logger
from airunner_common.get_logger import get_logger
from airunner_common.get_logger import set_log_base_path_resolver


def _path_settings_resolver() -> str:
    """Return the user-configured persistent log base path.

    Imported lazily so merely importing this shim never pulls in the database
    layer (and the GUI process never registers this resolver at all).
    """
    from airunner_services.database.models.path_settings import PathSettings

    settings = PathSettings.objects.first()
    base_path = getattr(settings, "base_path", None)
    if base_path:
        return base_path
    raise ValueError("PathSettings has no base_path")


set_log_base_path_resolver(_path_settings_resolver)


__all__ = ["Logger", "get_logger", "set_log_base_path_resolver"]
