"""Unit tests for ``GuiDaemonClient`` runtime control actions.

``_runtime_action`` declares ``metadata`` and ``timeout_seconds`` as
keyword-only arguments with no defaults, so every public wrapper has to
forward them.  ``cancel_runtime`` did not, which made it raise
``TypeError`` on every call (issue: TTS interrupt path).
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from airunner_services.daemon_client.gui_daemon_client import GuiDaemonClient


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> GuiDaemonClient:
    instance = GuiDaemonClient.__new__(GuiDaemonClient)
    calls: list[tuple[tuple, dict]] = []

    def _request(*args, **kwargs):
        calls.append((args, kwargs))
        return SimpleNamespace(json=lambda: {"status": "ok"})

    monkeypatch.setattr(instance, "_request", _request, raising=False)
    instance.recorded_calls = calls
    return instance


@pytest.mark.parametrize(
    "action", ["load_runtime", "unload_runtime", "cancel_runtime"]
)
def test_runtime_wrappers_forward_every_required_argument(
    client: GuiDaemonClient, action: str
) -> None:
    """Each wrapper must satisfy ``_runtime_action``'s keyword-only args."""
    result = getattr(client, action)(
        "tts",
        deployment_mode="sidecar",
        request_id="req-1",
    )

    assert result == {"status": "ok"}
    assert len(client.recorded_calls) == 1


def test_cancel_runtime_passes_metadata_and_timeout(
    client: GuiDaemonClient,
) -> None:
    """Explicit metadata/timeout reach the request body like the siblings."""
    client.cancel_runtime(
        "tts",
        deployment_mode="sidecar",
        request_id="req-1",
        metadata={"reason": "interrupt"},
        timeout_seconds=5.0,
    )

    args, kwargs = client.recorded_calls[0]
    assert args == ("POST", "/api/v1/daemon/runtimes/tts/cancel")
    assert kwargs["json_payload"]["metadata"] == {"reason": "interrupt"}
    assert kwargs["timeout_seconds"] == 5.0
