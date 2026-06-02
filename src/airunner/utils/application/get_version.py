"""Version helpers for AIRunner GUI code."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as package_version
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

PACKAGE_NAMES = (
    "airunner",
    "airunner-native",
    "airunner-services",
)

_CHECKOUT_SUBDIRS = ("services", "native")


def _load_checkout_version() -> str:
    """Return the repo version when running directly from a checkout."""
    current = Path(__file__).resolve()
    for candidate in current.parents:
        if not (candidate / "pyproject.toml").exists():
            continue
        for subdir in _CHECKOUT_SUBDIRS:
            module_path = candidate / subdir / "package_metadata.py"
            spec = spec_from_file_location(
                f"airunner_{subdir}_package_metadata",
                module_path,
            )
            if spec is None or spec.loader is None:
                continue
            module = module_from_spec(spec)
            spec.loader.exec_module(module)
            version = getattr(module, "VERSION", "")
            if version:
                return version
        return ""
    return ""


def get_version() -> str:
    """Return the current AIRunner version from installed metadata or
    checkout."""
    for package_name in PACKAGE_NAMES:
        try:
            return package_version(package_name)
        except PackageNotFoundError:
            continue
        except Exception:
            continue
    return _load_checkout_version()
