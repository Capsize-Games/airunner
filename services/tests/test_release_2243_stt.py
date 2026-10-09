"""Missing-runtime STT diagnostics (issue #2243, Gap 2).

The local STT fallback reports failure envelopes (mapped to 502,
like LLM/TTS) instead of raising into a bare 500.

CPU-only: no model, network, GPU, or database use.
"""

from __future__ import annotations

import base64
from typing import Any

from airunner_services.api.routes import stt_helpers
from airunner_services.ipc.messages import (
    EnvelopeStatus,
    ErrorEnvelope,
    RequestEnvelope,
    ResponseEnvelope,
)
from airunner_services.runtimes.contracts import (
    RuntimeAction,
    RuntimeKind,
)
from airunner_services.runtimes.local_fallback import (
    LocalFallbackSTTClient,
)


class _RaisingSource:
    """Signal source whose emit always fails like a missing backend."""

    def emit_signal(self, code: Any, data: Any) -> None:
        """Raise the missing-backend error the launcher reports."""
        raise RuntimeError("No whisper.cpp model is configured")


class _NullMediator:
    """Mediator double that tracks nothing."""

    def register(self, *args: Any, **kwargs: Any) -> None:
        """Accept one subscription without storing it."""
        return None

    def unregister(self, *args: Any, **kwargs: Any) -> None:
        """Accept one removal without storing anything."""
        return None


def _transcribe_request() -> RequestEnvelope:
    """Return one minimal STT invocation envelope."""
    audio_b64 = base64.b64encode(b"RIFF----WAVE").decode("ascii")
    return RequestEnvelope(
        runtime=RuntimeKind.STT,
        action=RuntimeAction.INVOKE,
        provider="local",
        payload={"audio_b64": audio_b64},
    )


def _failed_response(code: str) -> ResponseEnvelope:
    """Return one FAILED envelope carrying an error code."""
    return ResponseEnvelope(
        request_id="test",
        status=EnvelopeStatus.FAILED,
        error=ErrorEnvelope(code=code, message="backend failed"),
    )


def test_stt_local_transcribe_failure_envelope() -> None:
    """A raising STT backend becomes a FAILED envelope, not a raise."""
    client = LocalFallbackSTTClient(
        signal_source=_RaisingSource(),
        mediator=_NullMediator(),
    )
    response = client.invoke(_transcribe_request())
    assert response.status is EnvelopeStatus.FAILED
    assert response.error is not None
    assert response.error.code == "stt_invoke_failed"
    assert "whisper.cpp" in response.error.message


def test_stt_runtime_error_status_matches_llm_tts() -> None:
    """STT runtime failures map to 502 (504 for timeouts)."""
    assert stt_helpers.runtime_error_status(
        _failed_response("stt_invoke_failed")
    ) == 502
    assert stt_helpers.runtime_error_status(
        _failed_response("stt_timeout")
    ) == 504
