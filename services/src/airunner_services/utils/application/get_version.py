"""Version helpers for AIRunner service code."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as package_version


PACKAGE_NAMES = (
    "airunner",
    "airunner-native",
    "airunner-services",
    "airunner-common",
)


def _load_checkout_version() -> str:
    """Return the version when airunner_common is importable but not
    installed as a distribution -- e.g. a raw checkout with nothing
    pip-installed at all, only reachable via a PYTHONPATH.
    """
    try:
        from airunner_common.package_metadata import VERSION
    except ImportError:
        return ""
    return VERSION


def get_version() -> str:
    """Return the current AIRunner version from installed metadata or checkout."""
    for package_name in PACKAGE_NAMES:
        try:
            return package_version(package_name)
        except PackageNotFoundError:
            continue
        except Exception:
            continue
    return _load_checkout_version()
