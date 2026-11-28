"""Regression tests for issue #2485 (silent-swallow burn-down, slice 1).

Each test pins one narrowed ``except`` site: unexpected failures must
now propagate or log instead of silently returning a fallback that
callers mistake for success. CPU-only; every dependency is stubbed.
"""

from __future__ import annotations

import sys
import types
from importlib.metadata import PackageNotFoundError
from types import ModuleType, SimpleNamespace
from typing import Any
from unittest.mock import MagicMock

import pytest

from airunner_services.daemon_client import resource_store
from airunner_services.database.db import column as column_module
from airunner_services.model_management import model_registry
from airunner_services.preload_settings_store import LLMPreloadSettingsStore
import importlib as _importlib

get_version_module = _importlib.import_module(
    "airunner_services.utils.application.get_version"
)


# --- 1. get_version: only PackageNotFoundError is skipped -----------------


def test_get_version_unexpected_metadata_error_propagates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An unexpected metadata-backend failure must not become a version."""

    def _boom(_name: str) -> str:
        raise RuntimeError("metadata backend exploded")

    monkeypatch.setattr(get_version_module, "package_version", _boom)
    with pytest.raises(RuntimeError, match="metadata backend exploded"):
        get_version_module.get_version()


def test_get_version_missing_distributions_fall_through(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Missing distributions still fall through to the checkout version."""

    def _missing(_name: str) -> str:
        raise PackageNotFoundError(_name)

    monkeypatch.setattr(get_version_module, "package_version", _missing)
    assert (
        get_version_module.get_version()
        == get_version_module._load_checkout_version()
    )


# --- 2. model registry: only a missing catalog module is tolerated --------


def test_load_provider_config_missing_module_returns_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An uninstalled catalog module still means 'no legacy LLMs'."""

    def _missing(_name: str) -> Any:
        raise ModuleNotFoundError(
            "No module named 'airunner_services.llm.provider_config'",
            name="airunner_services.llm.provider_config",
        )

    monkeypatch.setattr(model_registry, "import_module", _missing)
    assert model_registry._load_provider_config() is None


def test_load_provider_config_broken_dependency_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A catalog module broken by its own bad import must not vanish."""

    def _broken(_name: str) -> Any:
        raise ModuleNotFoundError(
            "No module named 'some_third_party_dep'",
            name="some_third_party_dep",
        )

    monkeypatch.setattr(model_registry, "import_module", _broken)
    with pytest.raises(ModuleNotFoundError):
        model_registry._load_provider_config()


def test_load_provider_config_missing_attribute_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A catalog module without LLMProviderConfig must fail visibly."""

    monkeypatch.setattr(
        model_registry, "import_module", lambda _name: SimpleNamespace()
    )
    with pytest.raises(AttributeError):
        model_registry._load_provider_config()


# --- 3. _table_has_column: inspection failure raises, loudly ---------------


def test_table_has_column_inspection_error_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A failed inspection must not be reported as 'column missing'."""
    logger = MagicMock()

    def _boom(_bind: Any) -> Any:
        raise RuntimeError("database unreachable")

    monkeypatch.setattr("sqlalchemy.inspect", _boom)
    monkeypatch.setattr(column_module, "logger", logger)
    with pytest.raises(RuntimeError, match="database unreachable"):
        column_module._table_has_column(object(), "t", "c")
    assert logger.error.call_count == 1
    assert "Failed to inspect columns" in str(logger.error.call_args)


def test_table_has_column_reports_presence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The happy path still distinguishes present from absent columns."""

    class _Inspector:
        def get_columns(self, _table: str) -> list[dict[str, str]]:
            return [{"name": "id"}, {"name": "text_items"}]

    monkeypatch.setattr(
        "sqlalchemy.inspect", lambda _bind: _Inspector()
    )
    assert column_module._table_has_column(object(), "t", "text_items") is True
    assert column_module._table_has_column(object(), "t", "nope") is False


# --- 4. preload store: DB errors warn instead of vanishing -----------------


class _RecordingLogger:
    """Minimal injected logger capturing warning calls."""

    def __init__(self) -> None:
        self.warnings: list[str] = []

    def warning(self, message: str, *args: Any) -> None:
        self.warnings.append(message % args if args else message)

    def info(self, message: str, *args: Any) -> None:
        return None

    def debug(self, message: str, *args: Any) -> None:
        return None


def _failing_session(error: Exception) -> Any:
    session = MagicMock()
    session.query.side_effect = error
    return session


def test_first_enabled_llm_model_db_error_warns_and_returns_none() -> None:
    """A broken query resolves to 'no model' but says so out loud."""
    logger = _RecordingLogger()
    store = LLMPreloadSettingsStore(
        logger=logger, session_factory=MagicMock()
    )
    assert (
        store._first_enabled_llm_model(
            _failing_session(RuntimeError("db is gone"))
        )
        is None
    )
    assert any(
        "Could not query enabled LLM models" in message
        for message in logger.warnings
    )


def test_first_enabled_llm_model_db_error_without_logger() -> None:
    """The warning helper tolerates a missing injected logger."""
    store = LLMPreloadSettingsStore(
        logger=None, session_factory=MagicMock()
    )
    assert (
        store._first_enabled_llm_model(
            _failing_session(RuntimeError("db is gone"))
        )
        is None
    )


# --- 5. QSettings writes: missing Qt silent, failed writes logged ---------


def _stub_qsettings_module(
    monkeypatch: pytest.MonkeyPatch, module: ModuleType
) -> None:
    monkeypatch.setitem(
        sys.modules,
        "airunner_services.utils.settings.get_qsettings",
        module,
    )


def test_set_qsettings_value_missing_dependency_silent(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Headless daemons without Qt keep the old silent skip."""
    _stub_qsettings_module(monkeypatch, ModuleType("no_qt_stub"))
    with caplog.at_level("WARNING"):
        assert (
            resource_store._set_qsettings_value(
                "key", "value", group="application_settings"
            )
            is None
        )
    assert "Failed to persist QSettings" not in caplog.text


def test_set_qsettings_value_write_failure_logged(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A failed write must not vanish: it logs and keeps best-effort order."""
    calls: list[tuple[str, Any]] = []

    class _FailingSettings:
        def beginGroup(self, _group: str) -> None:
            return None

        def setValue(self, key: str, value: Any) -> None:
            calls.append((key, value))
            raise RuntimeError("disk is read-only")

        def endGroup(self) -> None:
            return None

        def sync(self) -> None:
            return None

    stub = ModuleType("qsettings_stub")
    stub.get_qsettings = lambda: _FailingSettings()  # type: ignore[attr-defined]
    _stub_qsettings_module(monkeypatch, stub)
    with caplog.at_level("WARNING"):
        assert (
            resource_store._set_qsettings_value(
                "dark_mode_enabled", True, group="application_settings"
            )
            is None
        )
    assert calls == [("dark_mode_enabled", True)]
    assert "Failed to persist QSettings value" in caplog.text


def test_set_qsettings_value_happy_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Successful writes still reach QSettings exactly once per call."""
    written: list[tuple[str, Any]] = []
    synced: list[bool] = []

    class _WorkingSettings:
        def beginGroup(self, _group: str) -> None:
            return None

        def setValue(self, key: str, value: Any) -> None:
            written.append((key, value))

        def endGroup(self) -> None:
            return None

        def sync(self) -> None:
            synced.append(True)

    stub = ModuleType("qsettings_working_stub")
    stub.get_qsettings = lambda: _WorkingSettings()  # type: ignore[attr-defined]
    _stub_qsettings_module(monkeypatch, stub)
    resource_store._set_qsettings_value(
        "dark_mode_enabled", True, group="application_settings"
    )
    assert written == [("dark_mode_enabled", True)]
    assert synced == [True]


def test_write_local_values_attempts_every_key(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """One failed key must not abort the remaining local-value writes."""

    class _FlakySettings:
        def beginGroup(self, _group: str) -> None:
            return None

        def setValue(self, key: str, _value: Any) -> None:
            if key == "first":
                raise RuntimeError("transient write failure")

        def endGroup(self) -> None:
            return None

        def sync(self) -> None:
            return None

    stub = ModuleType("qsettings_flaky_stub")
    stub.get_qsettings = lambda: _FlakySettings()  # type: ignore[attr-defined]
    _stub_qsettings_module(monkeypatch, stub)
    store = resource_store.GuiResourceStore.__new__(
        resource_store.GuiResourceStore
    )
    with caplog.at_level("WARNING"):
        store._write_local_values(
            "ApplicationSettings", {"first": True, "second": False}
        )
    assert "Failed to persist QSettings value" in caplog.text
