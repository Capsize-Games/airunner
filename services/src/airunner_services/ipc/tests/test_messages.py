"""Tests for transport-neutral IPC envelopes."""

from airunner_services.ipc.messages import (
    EnvelopeStatus,
    ErrorEnvelope,
    RequestEnvelope,
    ResponseEnvelope,
    StreamDelta,
)
from airunner_services.contracts_compat import RuntimeAction, RuntimeKind


class TestRequestEnvelope:
    """Tests for request envelope defaults."""

    def test_generates_request_id(self):
        request = RequestEnvelope(
            runtime=RuntimeKind.LLM,
            action=RuntimeAction.INVOKE,
        )

        assert request.request_id
        assert request.stream is False


class TestResponseEnvelope:
    """Tests for response envelope round trips."""

    def test_round_trips_payload_and_error(self):
        response = ResponseEnvelope(
            request_id="req-1",
            status=EnvelopeStatus.FAILED,
            error=ErrorEnvelope(code="runtime_failed", message="boom"),
            payload={"provider": "local"},
        )

        restored = ResponseEnvelope.model_validate(response.model_dump())

        assert restored.error is not None
        assert restored.error.code == "runtime_failed"
        assert restored.payload["provider"] == "local"


class TestStreamDelta:
    """Tests for streaming envelopes."""

    def test_defaults_to_stream_status(self):
        delta = StreamDelta(request_id="req-2", delta={"text": "hi"})

        assert delta.status is EnvelopeStatus.STREAM
        assert delta.final is False