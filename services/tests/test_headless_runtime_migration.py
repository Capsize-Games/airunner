"""Quiet first-boot knowledge migration (issue #2245).

Proves ``_run_knowledge_migration_if_needed`` defers quietly when
the database schema has no tables yet, while genuine failures still
log an error with a traceback. CPU-only; the session is stubbed.
"""

from __future__ import annotations

import importlib.util
import logging
import sqlite3
import types
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest
from sqlalchemy.exc import OperationalError

# The test venv editable-installs airunner_services from another
# checkout, so import the worktree module by file location.
MIXIN_PATH = (
    Path(__file__).resolve().parents[2]
    / "services"
    / "src"
    / "airunner_services"
    / "app"
    / "headless_runtime_mixin.py"
)


def _load_worktree_mixin() -> types.ModuleType:
    """Load the worktree mixin module in isolation."""
    found = importlib.util.spec_from_file_location(
        "headless_runtime_mixin_worktree_probe", MIXIN_PATH
    )
    assert found is not None and found.loader is not None
    module = importlib.util.module_from_spec(found)
    found.loader.exec_module(module)
    return module


class _Harness:
    """Minimal mixin host with an injected logger."""

    def __init__(
        self, mixin: types.ModuleType, logger: logging.Logger
    ) -> None:
        self._mixin = mixin
        self.logger = logger

    def run_migration(self) -> None:
        """Run the worktree migration check on this host."""
        bound = self._mixin.HeadlessRuntimeMixin
        bound._run_knowledge_migration_if_needed(self)


def _failing_scope(error: Exception) -> Any:
    """Return a session_scope stub whose first query raises."""
    session = MagicMock()
    chained = session.query.return_value.filter_by.return_value
    chained.with_for_update.return_value.first.side_effect = error
    scope = MagicMock()
    scope.__enter__.return_value = session
    return scope


def _missing_table_error() -> OperationalError:
    """Return the first-boot empty-database OperationalError."""
    orig = sqlite3.OperationalError("no such table: application_settings")
    return OperationalError("SELECT 1", {}, orig)


def _run_harness(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    error: Exception,
    logger_name: str,
) -> None:
    """Run the migration against a stub session raising error."""
    mixin = _load_worktree_mixin()
    monkeypatch.setattr(
        mixin, "session_scope", lambda: _failing_scope(error)
    )
    harness = _Harness(mixin, logging.getLogger(logger_name))
    with caplog.at_level(logging.DEBUG, logger=logger_name):
        harness.run_migration()


def test_missing_table_defers_quietly(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """No tables yet: an info deferral, no error, no traceback."""
    _run_harness(
        monkeypatch, caplog, _missing_table_error(), "test-mig-quiet"
    )
    assert not [
        record
        for record in caplog.records
        if record.levelno >= logging.ERROR
    ]
    assert any(
        "deferred to next startup" in record.getMessage()
        for record in caplog.records
    )


def test_genuine_failure_stays_loud(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Any other failure still logs an error with a traceback."""
    _run_harness(
        monkeypatch, caplog, ValueError("boom"), "test-mig-loud"
    )
    errors = [
        record
        for record in caplog.records
        if record.levelno >= logging.ERROR
    ]
    assert len(errors) == 1
    assert "will retry on next startup" in errors[0].getMessage()
    assert errors[0].exc_info is not None
