"""Schema and termination regressions for sidecar OpenAI-compatible data."""

from __future__ import annotations

import json
from typing import Any

import pytest

from airunner_services.runtimes.sidecar_openai_protocol import (
    SidecarRequestError,
    completion_payload,
    iter_openai_sse,
)


class _Response:
    def __init__(self, lines: list[bytes]) -> None:
        self._lines = iter(lines)

    def readline(self) -> bytes:
        return next(self._lines, b"")


def _event(data: dict[str, Any]) -> bytes:
    return b"data: " + json.dumps(data).encode("utf-8") + b"\n\n"


@pytest.mark.parametrize(
    "data",
    [
        {"choices": [{"message": {"content": ["wrong type"]}}]},
        {
            "choices": [{"message": {"content": "ok", "tool_calls": "wrong"}}],
        },
        {
            "choices": [{"message": {"content": "ok"}, "finish_reason": 4}],
        },
        {"choices": [{"message": {"content": "ok"}}], "usage": []},
        {"choices": [{"message": {"content": "ok"}}], "error": {"message": "failed"}},
    ],
)
def test_completion_normalizer_rejects_malformed_provider_fields(
    data: dict[str, Any],
) -> None:
    with pytest.raises(SidecarRequestError):
        completion_payload(data)


@pytest.mark.parametrize(
    "data",
    [
        {"choices": [{"delta": {"content": 3}}]},
        {"choices": [{"delta": {"tool_calls": [3]}}]},
        {"choices": [{"delta": {}, "finish_reason": 4}]},
        {"choices": [], "usage": []},
        {"choices": [{"text": 3}]},
        {"choices": [{"delta": {"content": "ok"}}], "usage": []},
    ],
)
def test_stream_parser_rejects_malformed_provider_fields(
    data: dict[str, Any],
) -> None:
    response = _Response([_event(data)])
    with pytest.raises(SidecarRequestError, match="malformed stream data"):
        list(iter_openai_sse(response))


@pytest.mark.parametrize(
    ("lines", "message"),
    [
        ([], "ended unexpectedly"),
        ([b"data: [DONE]\n\n"], "without a completion"),
    ],
)
def test_stream_parser_rejects_empty_or_truncated_stream(
    lines: list[bytes], message: str,
) -> None:
    with pytest.raises(SidecarRequestError, match=message):
        list(iter_openai_sse(_Response(lines)))
