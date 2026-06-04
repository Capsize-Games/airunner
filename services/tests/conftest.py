"""Shared pytest bootstrap for service-owned daemon tests."""

from __future__ import annotations

import sys
from pathlib import Path


_TEST_ROOT = Path(__file__).resolve().parent
_SERVICES_ROOT = _TEST_ROOT.parent
_PROJECT_ROOT = _SERVICES_ROOT.parent

for _path in (
    _TEST_ROOT,
    _TEST_ROOT / "eval",
    _PROJECT_ROOT / "services" / "src",
    _PROJECT_ROOT / "src",
):
    _path_str = str(_path)
    if _path_str not in sys.path:
        sys.path.append(_path_str)