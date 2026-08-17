"""Shared pytest fixtures for the ``application`` component test suites.

These suites (``application/tests`` and
``application/gui/widgets/paths/tests``) share the session-scoped
``QApplication`` and QSettings-backed client settings. A leftover ``qapp.api``
or ``qapp.main_window`` attribute from one test can bleed into the next
(GitHub issue #2055), so an autouse fixture scrubs that transient state after
every test. The fixture never creates a ``QApplication``; it only cleans up
when one already exists.
"""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _reset_shared_qt_state():
    """Remove transient QApplication attributes left by a previous test."""
    yield
    try:
        from PySide6.QtWidgets import QApplication
    except ImportError:  # pragma: no cover - non-GUI environment
        return
    app = QApplication.instance()
    if app is None:
        return
    for attribute in ("api", "main_window"):
        if hasattr(app, attribute):
            delattr(app, attribute)
