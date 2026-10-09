"""Quiet first-boot LLM preload (issue #2248).

Proves ``_resolve_preload_model_path`` defers quietly when the
database schema has no tables yet, while genuine failures still log
the pre-load warning. CPU-only; the settings store is stubbed.
"""

from __future__ import annotations

import logging
import sqlite3
from unittest.mock import MagicMock

import pytest
from sqlalchemy.exc import OperationalError

from airunner_services.lifecycle_service import CoreLifecycleService


def _missing_table_error() -> OperationalError:
    """Return the first-boot empty-database OperationalError."""
    orig = sqlite3.OperationalError("no such table: llm_generator_settings")
    return OperationalError("SELECT 1", {}, orig)


def _service_with_failing_store(
    error: Exception, logger_name: str
) -> CoreLifecycleService:
    """Return a service whose settings store raises error."""
    store = MagicMock()
    store.resolve_model_path.side_effect = error
    return CoreLifecycleService(
        signal_source=MagicMock(),
        logger=logging.getLogger(logger_name),
        preload_settings_store=store,
    )


def _messages(caplog: pytest.LogCaptureFixture) -> list[str]:
    """Return the captured log messages."""
    return [record.getMessage() for record in caplog.records]


def test_missing_table_preload_defers_quietly(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """No tables yet: an info deferral, no pre-load warning."""
    service = _service_with_failing_store(
        _missing_table_error(), "test-preload-quiet"
    )
    with caplog.at_level(logging.DEBUG, logger="test-preload-quiet"):
        assert service._resolve_preload_model_path() is None
    messages = _messages(caplog)
    assert not [
        message for message in messages if "Could not pre-load" in message
    ]
    assert any("deferred to first request" in m for m in messages)


def test_genuine_preload_failure_stays_loud(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Any other failure still logs the pre-load warning."""
    service = _service_with_failing_store(
        ValueError("boom"), "test-preload-loud"
    )
    with caplog.at_level(logging.DEBUG, logger="test-preload-loud"):
        assert service._resolve_preload_model_path() is None
    assert any(
        "Could not pre-load model" in message and "boom" in message
        for message in _messages(caplog)
    )
