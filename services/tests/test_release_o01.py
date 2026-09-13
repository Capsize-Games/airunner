"""Regression tests for release issue O01.

Proves the shared fetch boundary (airunner_services.url_safety) denies
external network access by default, requires an explicit operator
opt-in to allow it, and that SSRF protection still applies once online.

Also proves the frozen-dataclass exception bug this change exposed
(``SSRFBlocked``/``OfflineModeBlocked`` crashed with
``FrozenInstanceError`` instead of propagating cleanly through nested
context managers) is fixed.

No real network access: every check here only validates a URL string
or reaches the pre-network offline-mode gate before any socket would
ever open.
"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import FrozenInstanceError

import pytest

from airunner_common import settings as airunner_common_settings
from airunner_services.url_safety import (
    OfflineModeBlocked,
    SSRFBlocked,
    is_offline_mode,
    validate_url_for_fetch,
)


@pytest.fixture()
def offline(monkeypatch):
    monkeypatch.setattr(airunner_common_settings, "AIRUNNER_OFFLINE_MODE", True)


@pytest.fixture()
def online(monkeypatch):
    monkeypatch.setattr(airunner_common_settings, "AIRUNNER_OFFLINE_MODE", False)


def test_is_offline_mode_reflects_current_setting(monkeypatch) -> None:
    monkeypatch.setattr(airunner_common_settings, "AIRUNNER_OFFLINE_MODE", True)
    assert is_offline_mode() is True
    monkeypatch.setattr(airunner_common_settings, "AIRUNNER_OFFLINE_MODE", False)
    assert is_offline_mode() is False


def test_external_url_denied_by_default(offline) -> None:
    with pytest.raises(OfflineModeBlocked):
        validate_url_for_fetch("https://example.com")


def test_no_dns_resolution_is_attempted_while_offline(offline, monkeypatch) -> None:
    """Denial happens before any network-adjacent work, not just before
    the actual HTTP request."""

    def _fail_if_called(*_args, **_kwargs):
        raise AssertionError(
            "hostname resolution must not be attempted while offline"
        )

    monkeypatch.setattr(
        "airunner_services.url_safety._resolve_host_ips", _fail_if_called
    )
    with pytest.raises(OfflineModeBlocked):
        validate_url_for_fetch("https://example.com/whatever")


def test_explicit_opt_in_allows_external_url(online) -> None:
    # Does not raise OfflineModeBlocked; still subject to SSRF checks below.
    validate_url_for_fetch("https://example.com")


def test_ssrf_protection_still_applies_once_online(online) -> None:
    """Explicit online consent allows *external* network, not internal
    network — SSRF/private-IP protection is a separate, still-active
    layer checked after the offline-mode gate."""
    with pytest.raises(SSRFBlocked):
        validate_url_for_fetch("http://127.0.0.1/admin")


def test_offline_mode_denial_takes_precedence_over_ssrf_denial(offline) -> None:
    """Even an already-unsafe URL is denied for the offline-mode reason
    first: no network-adjacent work happens to discover it would have
    also been SSRF-blocked."""
    with pytest.raises(OfflineModeBlocked):
        validate_url_for_fetch("http://127.0.0.1/admin")


# --- Frozen-dataclass exception propagation (discovered while adding
# OfflineModeBlocked; both exception types must survive this) ---


@contextmanager
def _nested_context():
    yield


def _raise_through_nested_contexts(exc: Exception) -> None:
    with _nested_context():
        with _nested_context():
            raise exc


def test_ssrf_blocked_survives_nested_context_propagation() -> None:
    with pytest.raises(SSRFBlocked):
        _raise_through_nested_contexts(SSRFBlocked("test"))


def test_offline_mode_blocked_survives_nested_context_propagation() -> None:
    with pytest.raises(OfflineModeBlocked):
        _raise_through_nested_contexts(OfflineModeBlocked("test"))


def test_exceptions_are_not_frozen_dataclasses() -> None:
    """A regression guard: re-freezing either exception reintroduces the
    FrozenInstanceError crash proven above."""
    err = SSRFBlocked("test")
    err.reason = "mutated"  # must not raise FrozenInstanceError
    assert err.reason == "mutated"

    err2 = OfflineModeBlocked("test")
    err2.reason = "mutated"
    assert err2.reason == "mutated"


def test_compat_shim_reexports_new_symbols() -> None:
    """src/airunner/url_safety.py is a re-export shim (issue #2048); the
    new O01 symbols must be reachable through it too."""
    import airunner.url_safety as shim

    assert shim.OfflineModeBlocked is OfflineModeBlocked
    assert shim.is_offline_mode is is_offline_mode
