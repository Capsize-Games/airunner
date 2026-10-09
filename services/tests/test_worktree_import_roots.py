"""Regression test for issue #2246: tests must import this checkout.

The shared dev venv editable-installs the in-repo distributions from
one checkout. When pytest runs in another worktree reusing that venv,
the repo-root ``conftest.py`` (plus ``services/tests/conftest.py``)
pins this checkout's source trees ahead of the venv's pointers. This
test proves the pin holds: every in-repo top-level package must
resolve inside the checkout under test, never inside another checkout
that happens to own the venv's editable install.
"""

from __future__ import annotations

from pathlib import Path
from types import ModuleType

import airunner
import airunner_native
import airunner_services

_CHECKOUT_ROOT = Path(__file__).resolve().parents[2]

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
