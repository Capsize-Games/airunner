"""Service fallback must not turn an unavailable TTS backend into playback."""

from __future__ import annotations

from airunner_services.ipc.messages import EnvelopeStatus, RequestEnvelope
from airunner_services.runtimes.contracts import RuntimeAction, RuntimeKind
from airunner_services.runtimes.local_fallback import LocalFallbackTTSClient


class _SignalSource:
    def __init__(self) -> None:
        self._worker_manager = None
        self.played: list[str] = []
        self.signals: list[tuple[object, dict]] = []

    def play_audio(self, text: str) -> None:
        self.played.append(text)

    def emit_signal(self, signal: object, payload: dict) -> None:
        self.signals.append((signal, payload))


def _request() -> RequestEnvelope:
    return RequestEnvelope(
        request_id="tts-no-backend",
        runtime=RuntimeKind.TTS,
        action=RuntimeAction.INVOKE,
        payload={"text": "synthetic test phrase"},
    )


def test_unconfigured_service_fallback_fails_without_queueing_playback() -> None:
    source = _SignalSource()
    client = LocalFallbackTTSClient(signal_source=source)

    response = client.invoke(_request())

    assert response.status is EnvelopeStatus.FAILED
    assert response.error.code == "tts_backend_unavailable"
    assert source.played == []
    assert source.signals == []


def test_explicit_legacy_opt_in_preserves_interactive_playback() -> None:
    source = _SignalSource()
    client = LocalFallbackTTSClient(
        signal_source=source,
        allow_legacy_playback=True,
    )

    response = client.invoke(_request())

    assert response.status is EnvelopeStatus.SUCCEEDED
    assert response.payload == {"accepted": True}
    assert source.played == ["synthetic test phrase"]
