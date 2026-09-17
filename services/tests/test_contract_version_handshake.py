"""Regression tests for the desktop/daemon contract handshake (#2192).

Before this existed, nothing versioned the wire contract in
runtimes/contracts.py: a client and daemon of genuinely incompatible
builds would fail with an arbitrary attribute error at an arbitrary
point mid-conversation instead of being refused at connection time.
"""

from __future__ import annotations

from starlette.testclient import TestClient

from airunner_common.contract_version import (
    CONTRACT_VERSION,
    is_compatible_contract_version,
)
from airunner_services.api.server import create_app
from airunner_services.daemon_client.gui_daemon_client import (
    GuiDaemonClient,
)
from airunner_services.daemon_connection_state import (
    DaemonConnectionState,
)


def _bare_client() -> GuiDaemonClient:
    """A GuiDaemonClient with no __init__ side effects, for unit tests."""
    return GuiDaemonClient.__new__(GuiDaemonClient)


def test_health_endpoint_reports_the_contract_version() -> None:
    app = create_app(allowed_origins=["http://localhost"])
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["contract_version"] == CONTRACT_VERSION


def test_compatible_versions_agree_on_major() -> None:
    assert is_compatible_contract_version("1.0.0", "1.4.2") is True
    assert is_compatible_contract_version("1.9.9", "1.0.0") is True


def test_incompatible_versions_disagree_on_major() -> None:
    assert is_compatible_contract_version("1.0.0", "2.0.0") is False
    assert is_compatible_contract_version("2.3.1", "1.0.0") is False


def test_mismatch_reason_none_for_compatible_health() -> None:
    client = _bare_client()
    health = {"contract_version": CONTRACT_VERSION}
    assert client._contract_version_mismatch_reason(health) is None


def test_mismatch_reason_none_for_missing_health() -> None:
    client = _bare_client()
    assert client._contract_version_mismatch_reason(None) is None


def test_mismatch_reason_set_for_incompatible_major(monkeypatch) -> None:
    monkeypatch.setattr(
        "airunner_services.daemon_client.gui_daemon_client."
        "CONTRACT_VERSION",
        "1.0.0",
    )
    client = _bare_client()
    health = {"contract_version": "2.0.0"}
    reason = client._contract_version_mismatch_reason(health)
    assert reason is not None
    assert "1.0.0" in reason
    assert "2.0.0" in reason


def test_mismatch_reason_fails_closed_when_field_missing() -> None:
    """An old daemon build predating this field is not assumed safe."""
    client = _bare_client()
    health = {"status": "ready"}  # no contract_version key at all
    reason = client._contract_version_mismatch_reason(health)
    assert reason is not None
    assert "contract_version" in reason


def test_is_available_fails_on_contract_mismatch_without_recycling(
    monkeypatch,
) -> None:
    """A version mismatch is a hard failure, never a recycle-and-retry.

    Recycling a genuinely incompatible daemon build fixes nothing (it
    is not the same package staged with a newer build); only the
    stale-dev-build case should ever trigger a recycle.
    """
    client = _bare_client()
    client._last_error = ""
    client._state = DaemonConnectionState.NOT_STARTED

    def _set_state(state, reason):
        client._state = state
        client._last_error = reason

    client._set_state = _set_state
    client._healthcheck_payload = lambda timeout_seconds=0.2: {
        "contract_version": "99.0.0",
    }
    recycle_called = []
    client._recycle_stale_daemon = lambda reason: recycle_called.append(
        reason
    )

    result = client.is_available()

    assert result is False
    assert client._state is DaemonConnectionState.FAILED
    assert "99.0.0" in client._last_error
    assert recycle_called == []
