"""Unit tests for the TTS websocket synthesis helpers.

_validate_tts_request and _invoke_tts_runtime were extracted to keep
_synthesize within the long-function threshold. These tests pin the
validation error frames and the timeout/generic failure mappings.
"""

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

from airunner_services.api.routes.tts_ws import (
    _invoke_tts_runtime,
    _validate_tts_request,
)
from airunner_services.api.routes.tts_models import TTSRequest


def _ws():
    return SimpleNamespace(send_json=AsyncMock(return_value=None))


def _request():
    return TTSRequest(text="hi", speed=1.0)


def test_validate_accepts_good_request():
    ws = _ws()
    request = asyncio.run(
        _validate_tts_request(ws, {"text": "hello", "voice": "bob", "speed": 1.5})
    )
    assert request is not None
    assert request.text == "hello"
    ws.send_json.assert_not_called()


def test_validate_rejects_bad_speed():
    ws = _ws()
    assert (
        asyncio.run(_validate_tts_request(ws, {"text": "hi", "speed": 99}))
        is None
    )
    ws.send_json.assert_called_once_with(
        {"type": "error", "message": "invalid_speed"}
    )


def test_validate_rejects_non_numeric_speed():
    ws = _ws()
    assert (
        asyncio.run(
            _validate_tts_request(ws, {"text": "hi", "speed": "fast"})
        )
        is None
    )
    ws.send_json.assert_called_once_with(
        {"type": "error", "message": "invalid_speed"}
    )


def test_validate_rejects_empty_text():
    ws = _ws()
    assert asyncio.run(_validate_tts_request(ws, {"text": "   "})) is None
    ws.send_json.assert_called_once_with(
        {"type": "error", "message": "text is required"}
    )


def test_invoke_success_returns_response():
    ws = _ws()
    client = MagicMock()
    client.invoke.return_value = "resp"
    out = asyncio.run(_invoke_tts_runtime(ws, client, _request(), None, 5))
    assert out == "resp"


def test_invoke_timeout_maps_to_frame():
    ws = _ws()
    client = MagicMock()

    def _slow(envelope):
        import time

        time.sleep(1)
        return "x"

    client.invoke.side_effect = _slow
    out = asyncio.run(_invoke_tts_runtime(ws, client, _request(), None, 0.05))
    assert out is None
    ws.send_json.assert_called_once_with(
        {"type": "error", "message": "synthesis_timeout"}
    )


def test_invoke_generic_error_maps_to_frame():
    ws = _ws()
    client = MagicMock()
    client.invoke.side_effect = RuntimeError("nope")
    out = asyncio.run(_invoke_tts_runtime(ws, client, _request(), None, 5))
    assert out is None
    ws.send_json.assert_called_once_with(
        {"type": "error", "message": "synthesis_failed"}
    )
