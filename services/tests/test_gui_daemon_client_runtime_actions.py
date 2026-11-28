"""Runtime-control wrappers on GuiDaemonClient forward their arguments.

The daemon control helper requires its keyword arguments on every call;
these tests pin the three public wrappers (load/unload/cancel) against
that contract by capturing what they pass to the helper.
"""

from __future__ import annotations

from unittest.mock import Mock

import pytest

from airunner_services.daemon_client.gui_daemon_client import GuiDaemonClient


@pytest.fixture
def captured_client(monkeypatch: pytest.MonkeyPatch) -> GuiDaemonClient:
    client = GuiDaemonClient.__new__(GuiDaemonClient)
    client.forwarded = Mock(return_value={"status": "ok"})
    monkeypatch.setattr(client, "_runtime_action", client.forwarded, raising=False)
    return client


@pytest.mark.parametrize(
    ("method_name", "expected_action"),
    [
        ("load_runtime", "load"),
        ("unload_runtime", "unload"),
        ("cancel_runtime", "cancel"),
    ],
)
def test_each_wrapper_reaches_the_helper(captured_client, method_name, expected_action):
    outcome = getattr(captured_client, method_name)(
        "stt", request_id="r-42", metadata={"origin": "test"}, timeout_seconds=2.5
    )

    assert outcome == {"status": "ok"}
    kwargs = captured_client.forwarded.call_args.kwargs
    assert kwargs["metadata"] == {"origin": "test"}
    assert kwargs["timeout_seconds"] == 2.5
    assert kwargs["request_id"] == "r-42"


def test_cancel_does_not_auto_start_by_default(captured_client):
    captured_client.cancel_runtime("stt")

    assert captured_client.forwarded.call_args.kwargs["auto_start"] is False
