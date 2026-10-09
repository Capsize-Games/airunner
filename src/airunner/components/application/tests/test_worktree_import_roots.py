"""Regression test for issue #2246: src tests must import this checkout.

Same pin as ``services/tests/test_worktree_import_roots.py``, proven
for the ``src`` suite: the repo-root ``conftest.py`` moves this
checkout's source trees ahead of the shared venv's editable-install
pointers, so ``airunner`` resolves inside the checkout under test even
when the venv's editable install belongs to another checkout.
"""

from __future__ import annotations

from pathlib import Path
from types import ModuleType

import airunner
import airunner_native
import airunner_services

_CHECKOUT_ROOT = Path(__file__).resolve().parents[5]

_PACKAGES: dict[str, ModuleType] = {
    "airunner": airunner,
    "airunner_native": airunner_native,
    "airunner_services": airunner_services,
}


def test_in_repo_packages_resolve_to_checkout_under_test() -> None:
    """Every in-repo package must resolve inside this checkout."""
    for name, package in _PACKAGES.items():
        assert package.__file__ is not None, f"{name} has no __file__"
        location = Path(package.__file__).resolve()
        assert location.is_relative_to(_CHECKOUT_ROOT), (
            f"{name} resolves to {location}, outside the checkout "
            f"under test ({_CHECKOUT_ROOT}); the suite would exercise "
            "another checkout's sources (issue #2246)."
        )
