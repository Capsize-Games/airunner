"""Managed-daemon launch prep uses service-owned test-mode setup."""

from __future__ import annotations

import importlib
import sys
from typing import Callable

import pytest

from airunner_services.bin.airunner_headless import (
    _prepare_managed_daemon_launch as prepare_headless_launch,
)
from airunner_services.runtimes.sidecar_tts_launcher import (
    _prepare_managed_daemon_launch as prepare_tts_launch,
)
from airunner_services.runtimes.sidecar_art_launcher import (
    _prepare_managed_daemon_launch as prepare_art_launch,
)

_PREPARERS: tuple[Callable[[], None], ...] = (
    prepare_headless_launch,
    prepare_tts_launch,
    prepare_art_launch,
)


def _block_airunner_native(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make any airunner_native import fail like a missing install."""
    monkeypatch.setitem(sys.modules, "airunner_native", None)
    monkeypatch.setitem(sys.modules, "airunner_native.launcher", None)


def _stub_setup_database(
    monkeypatch: pytest.MonkeyPatch,
) -> list[bool]:
    """Replace setup_database with a recording no-op."""
    calls: list[bool] = []

    def fake_setup_database() -> None:
        calls.append(True)

    module = importlib.import_module(
        "airunner_services.database.setup_database"
    )
    monkeypatch.setattr(module, "setup_database", fake_setup_database)
    return calls


@pytest.mark.parametrize("prepare", _PREPARERS)
def test_launch_prep_skips_native_outside_test_env(
    prepare: Callable[[], None],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Non-test launch prep runs DB setup without native present."""
    monkeypatch.delenv("AIRUNNER_ENVIRONMENT", raising=False)
    _block_airunner_native(monkeypatch)
    calls = _stub_setup_database(monkeypatch)

    prepare()

    assert calls == [True]


@pytest.mark.parametrize("prepare", _PREPARERS)
def test_launch_prep_configures_test_mode_without_native(
    prepare: Callable[[], None],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test-mode launch preparation works without native installed."""
    monkeypatch.setenv("AIRUNNER_ENVIRONMENT", "test")
    _block_airunner_native(monkeypatch)
    _stub_setup_database(monkeypatch)
    calls: list[bool] = []
    module = importlib.import_module("airunner_services.config.test_mode")
    monkeypatch.setattr(
        module,
        "configure_test_mode",
        lambda: calls.append(True),
    )

    prepare()
    assert calls == [True]


def test_configure_test_mode_creates_temp_database_settings(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test-mode setup creates service settings and honors model override."""
    from airunner_services.config.test_mode import configure_test_mode
    from airunner_services.database.models.application_settings import (
        ApplicationSettings,
    )
    from airunner_services.database.models.llm_generator_settings import (
        LLMGeneratorSettings,
    )
    from airunner_services.database.models.path_settings import PathSettings
    from airunner_services.database.session import reset_engine, session_scope
    from airunner_services.database.setup_database import setup_database

    monkeypatch.setenv(
        "AIRUNNER_DATABASE_URL",
        f"sqlite:///{tmp_path / 'test-mode.sqlite3'}",
    )
    monkeypatch.setenv("AIRUNNER_DISABLE_DB_SETUP_CACHE", "1")
    monkeypatch.setenv("AIRUNNER_TEST_MODEL_PATH", str(tmp_path / "model"))
    reset_engine()
    setup_database()
    try:
        configure_test_mode()
        configure_test_mode()

        assert PathSettings.objects.first() is not None
        assert ApplicationSettings.objects.first() is not None
        llm_settings = LLMGeneratorSettings.objects.first()
        assert llm_settings is not None
        assert llm_settings.model_path == str(tmp_path / "model")
        with session_scope() as session:
            assert session.query(PathSettings).count() == 1
            assert session.query(ApplicationSettings).count() == 1
            assert session.query(LLMGeneratorSettings).count() == 1
    finally:
        reset_engine()
