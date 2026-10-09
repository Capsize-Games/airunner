"""PyInstaller runtime hook: frozen-safe transformers import scan.

transformers builds its lazy ``models`` import structure at import
time by scanning ``.py`` sources (``define_import_structure``). The
per-package ``__init__`` files pass their own ``__file__``; upstream
falls back to the parent directory only when that path
``isfile()``. In the frozen bundle ``__file__`` points at a
``__init__.pyc`` that lives only inside the PYZ, so the check fails
and the scan dies with FileNotFoundError before the daemon serves
(issue #2245).

The hook wraps ``create_import_structure_from_path`` so any path
that is not a real directory scans its parent instead -- the
documented upstream behavior for file input -- which is the
``pyz+py`` collected sources tree. Import-time side effects run only
when frozen; importing this module unfrozen is a no-op.
"""

from __future__ import annotations

import importlib.util
import os
import sys
import types
from typing import Any, Callable


def resolve_scan_dir(module_path: str | os.PathLike[str]) -> str:
    """Return the directory transformers should scan for sources."""
    if os.path.isdir(module_path):
        return os.fspath(module_path)
    return os.path.dirname(os.fspath(module_path))


def patch_create_import_structure(
    import_utils: types.ModuleType,
) -> Callable[..., Any]:
    """Wrap the import scan with the frozen-dirname fallback."""
    original = import_utils.create_import_structure_from_path

    def frozen_safe(*args: Any, **kwargs: Any) -> Any:
        """Scan the parent dir when the path is not a directory."""
        scanned = (resolve_scan_dir(args[0]),) + tuple(args[1:])
        return original(*scanned, **kwargs)

    import_utils.create_import_structure_from_path = frozen_safe
    return frozen_safe


def _transformers_shipped() -> bool:
    """True when the frozen app ships the transformers package."""
    return importlib.util.find_spec("transformers") is not None


def main() -> None:
    """Patch the frozen transformers import scan, when shipped."""
    if not _transformers_shipped():
        return
    from transformers.utils import import_utils

    patch_create_import_structure(import_utils)


if getattr(sys, "frozen", False):
    main()
