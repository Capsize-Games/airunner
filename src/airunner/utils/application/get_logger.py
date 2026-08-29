"""GUI-side re-export of the shared AIRunner logger factory.

The canonical implementation lives in :mod:`airunner_common.get_logger`
(issue #2050). This module is a thin shim; the GUI process does not register a
``PathSettings``-based log base path resolver (it has none), so file logging
falls back to the shared default base path.
"""

from __future__ import annotations

from typing import Optional

from airunner_common.get_logger import Logger
from airunner_common.get_logger import get_logger
from airunner_common.get_logger import set_log_base_path_resolver

__all__ = ["Logger", "get_logger", "set_log_base_path_resolver"]
