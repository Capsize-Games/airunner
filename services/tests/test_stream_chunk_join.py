"""Chunk-join regression tests for Capsize-Games/airunnerweb#159.

llama.cpp detokenization already embeds real inter-token spaces, so the
streaming callbacks must forward token fragments verbatim with plain
concatenation. Routing fragments through ``prepare_stream_chunk``
inserts a space at every alnum->alnum boundary and splits BPE subwords
apart (``air unner``, ``hugging face``).
"""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from types import SimpleNamespace
from typing import Any

import pytest

from airunner_services.api.routes.legacy_ollama_compat import (
    _ollama_chat_stream,
)
from airunner_services.llm.llm_request import LLMRequest
from airunner_services.llm.managers.mixins import generation_signal_support
from airunner_services.llm.managers.mixins import generation_stream_support

_SUBWORD_CHUNKS = [
    "air",
    "unner",
    " ",
    "res",
    "olvable",
    " ",
    "hugging",
    "face",
]
_SUBWORD_JOINED = "airunner resolvable huggingface"

_CAMEL_CHUNKS = [
    "check ",
    "myVariableName",
    " in ",
    "theHuggingfaceRepo",
    " now",
]
_CAMEL_JOINED = "check myVariableName in theHuggingfaceRepo now"


def _make_owner(signals: list) -> SimpleNamespace:
    """Build a minimal generation owner capturing stream signals."""
    llm = SimpleNamespace(
        send_llm_text_streamed_signal=signals.append,
    )
    return SimpleNamespace(
        api=SimpleNamespace(llm=llm),
        logger=logging.getLogger("test_stream_chunk_join"),
        _current_request_id="req-chunk-join",
        _workflow_manager=None,
        _interrupted=False,
    )


@pytest.mark.parametrize(
    "module",
    [generation_signal_support, generation_stream_support],
    ids=["live", "publication_gated"],
)
def test_streaming_callback_joins_subwords_without_spaces(
    module: Any,
) -> None:
    """Subword fragments must join with no inserted boundary spaces."""
    signals: list = []
    owner = _make_owner(signals)
    request = SimpleNamespace(node_id="node-chunk-join")
    complete = [""]
    sequence = [0]
    on_token = module.create_streaming_callback(
        owner, request, complete, sequence
    )
    for chunk in _SUBWORD_CHUNKS:
        on_token(chunk)
    assert complete[0] == _SUBWORD_JOINED
    if module is generation_signal_support:
        assert [s.message for s in signals] == _SUBWORD_CHUNKS
    else:
        assert signals == []


class _FakeDaemonLLM:
    """Drive the Ollama stream callback with canned fragments."""

    def __init__(self, chunks: list[str]) -> None:
        self._chunks = chunks

    def send_request(self, **kwargs: Any) -> None:
        """Replay canned fragments then the end-of-message marker."""
        callback: Callable[[dict[str, Any]], None] = kwargs["callback"]
        for piece in self._chunks:
            callback(
                {
                    "response": SimpleNamespace(
                        message=piece,
                        is_end_of_message=False,
                        message_type="assistant",
                        tool_calls=None,
                        final_visible_message=None,
                    )
                }
            )
        callback(
            {
                "response": SimpleNamespace(
                    message="",
                    is_end_of_message=True,
                    message_type="assistant",
                    tool_calls=None,
                    final_visible_message=None,
                )
            }
        )


def test_ollama_chat_stream_preserves_camel_case_and_words() -> None:
    """Ollama deltas must preserve camelCase identifiers verbatim."""
    app = SimpleNamespace(llm=_FakeDaemonLLM(_CAMEL_CHUNKS))
    lines = list(
        _ollama_chat_stream(
            app, "prompt", "airunner:latest", LLMRequest(), "req-camel"
        )
    )
    assert lines
    payloads = [json.loads(line.decode("utf-8")) for line in lines]
    assert payloads[-1]["done"] is True
    assert payloads[-1]["message"]["content"] == ""
    joined = "".join(p["message"]["content"] for p in payloads[:-1])
    assert joined == _CAMEL_JOINED
