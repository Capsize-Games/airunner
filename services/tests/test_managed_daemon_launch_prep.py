"""Managed-daemon launch prep must not require airunner_native.

Every ``_prepare_managed_daemon_launch`` only needs
``airunner_native.launcher._configure_test_mode`` when
``AIRUNNER_ENVIRONMENT=test``. Importing it unconditionally made the
services-only ``airunner-headless`` boot die with
``ModuleNotFoundError: No module named 'airunner_native'`` in an
environment where the native package is not installed (W16). The
art sidecar launcher already imported it inside the test branch;
these tests pin the same shape for the headless supervisor and the
TTS sidecar launcher.
"""

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

_PREPARERS: tuple[Callable[[], None], ...] = (
    prepare_headless_launch,
    prepare_tts_launch,
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
def test_launch_prep_imports_native_only_in_test_env(
    prepare: Callable[[], None],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """In test env the native helper is still imported and fails."""
    monkeypatch.setenv("AIRUNNER_ENVIRONMENT", "test")
    _block_airunner_native(monkeypatch)
    _stub_setup_database(monkeypatch)

    with pytest.raises(ModuleNotFoundError):
        prepare()
