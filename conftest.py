"""Repo-root pytest bootstrap: pin imports to the checkout under test.

Issue #2246: the shared dev venv editable-installs ``airunner``,
``airunner_native`` and ``airunner_services`` from one checkout (plain
``.pth`` path entries, or ``__editable__`` meta-path finders in strict
editable mode). When pytest runs in another worktree reusing that
venv, those entries resolve first and the suite silently exercises the
wrong checkout's sources.

pytest imports this file before any test module, and the repo-root
``pyproject.toml`` is the only pytest config, so this one file covers
both suites (``src`` and ``services/tests``): it moves this checkout's
source trees to the front of ``sys.path`` and drops any
already-imported in-repo package that resolved outside this checkout
so its next import picks up this checkout's sources.
"""

from __future__ import annotations

import sys
from pathlib import Path
from types import ModuleType

_CHECKOUT_ROOT = Path(__file__).resolve().parent

# In-repo distributions, each providing one top-level package from its
# own source tree. airunner_common is a real installed dependency from
# its own repository (issue #2197), not a local path, so it is neither
# pinned nor purged here.
_SOURCE_DIRS = (
    _CHECKOUT_ROOT / "services" / "src",
    _CHECKOUT_ROOT / "native" / "src",
    _CHECKOUT_ROOT / "src",
)
_PINNED_TOP_LEVELS = frozenset(
    {"airunner", "airunner_native", "airunner_services"}
)
_EDITABLE_FINDER_PREFIX = "__editable__"


def _pin_checkout_sources() -> None:
    """Move this checkout's source trees to the front of sys.path."""
    entries = [str(path) for path in _SOURCE_DIRS]
    sys.path[:] = [entry for entry in sys.path if entry not in entries]
    sys.path[0:0] = entries


def _module_location(module: ModuleType) -> Path | None:
    """Return where an imported module was loaded from, if known."""
    file = getattr(module, "__file__", None)
    if file is not None:
        return Path(file)
    search_path = getattr(module, "__path__", None)
    if search_path:
        first = next(iter(search_path), None)
        if first is not None:
            return Path(first)
    return None


def _is_foreign(location: Path) -> bool:
    """Return whether a path lives outside this checkout."""
    try:
        return not location.resolve().is_relative_to(_CHECKOUT_ROOT)
    except OSError:
        return False


def _purge_foreign_modules() -> None:
    """Drop in-repo packages already imported from another checkout."""
    for name in list(sys.modules):
        if name.split(".", 1)[0] not in _PINNED_TOP_LEVELS:
            continue
        module = sys.modules[name]
        if module is None:
            del sys.modules[name]
            continue
        location = _module_location(module)
        if location is not None and _is_foreign(location):
            del sys.modules[name]


def _finder_targets_foreign(finder: object) -> bool:
    """Return whether an editable finder maps our packages elsewhere."""
    module_name = getattr(finder, "__module__", "")
    if not module_name.startswith(_EDITABLE_FINDER_PREFIX):
        return False
    mapping = getattr(sys.modules.get(module_name), "MAPPING", None)
    if not isinstance(mapping, dict):
        return False
    for top_level, target in mapping.items():
        if not isinstance(target, str):
            continue
        if top_level in _PINNED_TOP_LEVELS and _is_foreign(Path(target)):
            return True
    return False


def _drop_foreign_editable_finders() -> None:
    """Drop strict-mode editable finders aimed at another checkout."""
    sys.meta_path[:] = [
        finder
        for finder in sys.meta_path
        if not _finder_targets_foreign(finder)
    ]


_pin_checkout_sources()
_purge_foreign_modules()
_drop_foreign_editable_finders()
