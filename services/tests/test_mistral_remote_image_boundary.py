"""Ensure native Mistral tokenization never fetches caller-supplied image URLs."""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from langchain_core.messages import HumanMessage

from airunner_services.llm.adapters.mixins import message_formatting_mixin as formatting


class _CaptureMessage:
    def __init__(self, *, content):
        self.content = content


def _converter(monkeypatch: pytest.MonkeyPatch) -> formatting.MessageFormattingMixin:
    monkeypatch.setattr(
        formatting, "MistralUserMessage", _CaptureMessage, raising=False
    )
    monkeypatch.setattr(
        formatting, "MistralSystemMessage", _CaptureMessage, raising=False
    )
    monkeypatch.setattr(
        formatting, "MistralAssistantMessage", _CaptureMessage, raising=False
    )
    return object.__new__(formatting.MessageFormattingMixin)


@pytest.mark.parametrize(
    "content",
    [
        [{"type": "image_url", "image_url": {"url": "https://example.invalid/x.png"}}],
        [{"type": "image_url", "image_url": "http://example.invalid/x.png"}],
        [{"type": "image", "image": "https://example.invalid/x.png"}],
        [{"type": "image", "image": {"url": "https://example.invalid/x.png"}}],
        [
            SimpleNamespace(
                type="image_url",
                image_url=SimpleNamespace(url="https://example.invalid/x.png"),
            )
        ],
    ],
)
def test_native_mistral_rejects_remote_image_references(
    monkeypatch: pytest.MonkeyPatch, content: list[object]
) -> None:
    converter = _converter(monkeypatch)
    message = (
        SimpleNamespace(content=content)
        if any(not isinstance(part, dict) for part in content)
        else HumanMessage(content=content)
    )

    with pytest.raises(formatting.MistralRemoteImageUnsupportedError) as exc_info:
        converter._convert_messages_to_mistral([message])

    assert exc_info.value.code == "remote_image_url_unsupported_for_mistral_native"
    assert str(exc_info.value) == exc_info.value.code


def test_native_mistral_keeps_inline_images_and_text_urls(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    converter = _converter(monkeypatch)
    content = [
        {"type": "text", "text": "See https://example.invalid/page"},
        {"type": "image_url", "image_url": {"url": "data:image/png;base64,AA=="}},
        {"type": "image", "image": "file:///tmp/local-image.png"},
    ]

    result = converter._convert_messages_to_mistral([HumanMessage(content=content)])

    assert len(result) == 1
    assert result[0].content == content
