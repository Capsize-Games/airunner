"""The TTS route returns completed WAV bytes without line-streaming them."""

from __future__ import annotations

import asyncio
import base64
import io
from types import SimpleNamespace
import wave

import pytest
from fastapi import HTTPException
from starlette.requests import Request


def _binary_wav_with_many_newlines() -> bytes:
    """Build valid PCM WAV bytes with many newline-valued payload bytes."""
    output = io.BytesIO()
    with wave.open(output, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(22050)
        wav_file.writeframes(b"\x0a\x00" * 4096)
    data = output.getvalue()
    assert data.count(b"\n") > 4000
    return data


def test_tts_route_returns_complete_binary_wav_in_one_asgi_body(monkeypatch) -> None:
    from airunner_services.api.routes.tts import synthesize_speech
    from airunner_services.api.server import authenticate_connection
    from airunner_services.api.routes.tts_models import TTSHTTPRequest
    from airunner_services.ipc.messages import (
        EnvelopeStatus,
        ErrorEnvelope,
        ResponseEnvelope,
    )
    from airunner_services.runtimes.contracts import RuntimeKind, RuntimeMode
    from airunner_services.runtimes.registry import RuntimeRegistry, RuntimeRoute

    async def run_inline(function, *args, **kwargs):
        return function(*args, **kwargs)

    monkeypatch.setattr(
        "airunner_services.api.routes.tts.asyncio.to_thread",
        run_inline,
    )

    wav_data = _binary_wav_with_many_newlines()

    class FakeTTSClient:
        failure = False
        invoke_count = 0

        def invoke(self, request):
            self.invoke_count += 1
            if self.failure:
                return ResponseEnvelope(
                    request_id=request.request_id,
                    status=EnvelopeStatus.FAILED,
                    error=ErrorEnvelope(
                        code="tts_backend_unavailable",
                        message="fixture backend unavailable",
                        retryable=True,
                    ),
                )
            return ResponseEnvelope(
                request_id=request.request_id,
                status=EnvelopeStatus.SUCCEEDED,
                payload={"audio_b64": base64.b64encode(wav_data).decode("ascii")},
            )

        def healthcheck(self):
            raise AssertionError("synthesis must not request a health check")

    tts_client = FakeTTSClient()
    registry = RuntimeRegistry()
    registry.register(
        RuntimeRoute(
            RuntimeKind.TTS,
            provider="local",
            deployment_mode=RuntimeMode.LOCAL_FALLBACK.value,
        ),
        tts_client,
    )
    app = SimpleNamespace(state=SimpleNamespace(runtime_registry=registry))

    def request_with_auth(auth_header: bytes | None) -> Request:
        headers = []
        if auth_header is not None:
            headers.append((b"authorization", auth_header))
        return Request(
            {
                "type": "http",
                "asgi": {"version": "3.0", "spec_version": "2.3"},
                "http_version": "1.1",
                "method": "POST",
                "scheme": "http",
                "path": "/api/v1/tts/synthesize",
                "raw_path": b"/api/v1/tts/synthesize",
                "query_string": b"",
                "headers": headers,
                "client": ("127.0.0.1", 43210),
                "server": ("127.0.0.1", 8000),
                "root_path": "",
                "app": app,
            }
        )

    unauthorized = request_with_auth(None)
    authenticated = request_with_auth(b"Bearer fixture-api-key")
    assert authenticate_connection(
        unauthorized,
        api_key="fixture-api-key",
        require_api_key=True,
        insecure_no_auth=False,
        allow_query_token=False,
    ) == (False, 401)
    assert authenticate_connection(
        authenticated,
        api_key="fixture-api-key",
        require_api_key=True,
        insecure_no_auth=False,
        allow_query_token=False,
    ) == (True, 200)

    request = TTSHTTPRequest(
        text="fixture",
        model_type="Espeak",
        request_id="buffered-wav-regression",
    )
    response = asyncio.run(synthesize_speech(request, authenticated))

    messages: list[dict[str, object]] = []

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message):
        messages.append(message.copy())

    response_scope = {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "2.3"},
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": "/api/v1/tts/synthesize",
        "raw_path": b"/api/v1/tts/synthesize",
        "query_string": b"",
        "headers": [],
        "client": ("127.0.0.1", 43210),
        "server": ("127.0.0.1", 8000),
        "root_path": "",
    }
    asyncio.run(response(response_scope, receive, send))

    start_message = next(
        message for message in messages
        if message.get("type") == "http.response.start"
    )
    response_headers = dict(start_message["headers"])
    body_messages = [
        message for message in messages
        if message.get("type") == "http.response.body"
        and message.get("body")
    ]
    assert start_message["status"] == 200
    assert response_headers[b"content-type"] == b"audio/wav"
    assert response_headers[b"content-length"] == str(len(wav_data)).encode()
    assert len(body_messages) == 1
    assert body_messages[0]["body"] == wav_data
    assert wav_data.startswith(b"RIFF") and wav_data[8:12] == b"WAVE"
    assert tts_client.invoke_count == 1

    tts_client.failure = True
    with pytest.raises(HTTPException) as error:
        asyncio.run(synthesize_speech(request, authenticated))
    assert error.value.status_code == 503
    assert error.value.detail == "tts_backend_unavailable"
