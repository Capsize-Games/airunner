"""Helpers for building HuggingFace chat-template payloads."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)


@dataclass
class ChatTemplatePayload:
    """Prepared chat-template payload for one prompt."""

    chat_messages: list[dict[str, Any]] = field(default_factory=list)
    extracted_images: list[Any] = field(default_factory=list)
    image_placeholders: int = 0


def build_chat_template_payload(
    adapter: Any,
    messages: list[BaseMessage],
) -> ChatTemplatePayload:
    """Convert LangChain messages into template-ready payload data."""
    payload = ChatTemplatePayload()
    for message in messages:
        _append_chat_message(adapter, payload, message)
    return payload


def _append_chat_message(
    adapter: Any,
    payload: ChatTemplatePayload,
    message: BaseMessage,
) -> None:
    """Append one message to the template payload."""
    if isinstance(message, SystemMessage):
        payload.chat_messages.append(_system_message(message))
        return
    if isinstance(message, HumanMessage):
        _append_human_message(adapter, payload, message)
        return
    if isinstance(message, AIMessage):
        payload.chat_messages.append(_assistant_message(message))
        return
    if isinstance(message, ToolMessage):
        payload.chat_messages.append(_tool_message(message))


def _system_message(message: SystemMessage) -> dict[str, Any]:
    """Return one chat-template system message."""
    return {"role": "system", "content": message.content}


def _append_human_message(
    adapter: Any,
    payload: ChatTemplatePayload,
    message: HumanMessage,
) -> None:
    """Append one human message, keeping only the latest image inputs."""
    payload.extracted_images = []
    payload.image_placeholders = 0
    if not isinstance(message.content, list):
        payload.chat_messages.append(
            {"role": "user", "content": message.content}
        )
        return
    content, images, placeholders = _build_human_content(
        adapter, message.content
    )
    payload.chat_messages.append({"role": "user", "content": content})
    payload.extracted_images.extend(images)
    payload.image_placeholders = placeholders


def _build_human_content(
    adapter: Any,
    parts: list[Any],
) -> tuple[list[dict[str, Any]], list[Any], int]:
    """Build multimodal content parts for one human message."""
    content_parts: list[dict[str, Any]] = []
    extracted_images: list[Any] = []
    placeholders = 0
    for part in parts:
        placeholders += _append_content_part(
            adapter,
            content_parts,
            extracted_images,
            part,
        )
    return content_parts, extracted_images, placeholders


def _append_content_part(
    adapter: Any,
    content_parts: list[dict[str, Any]],
    extracted_images: list[Any],
    part: Any,
) -> int:
    """Append one human content part and return new image placeholders."""
    if isinstance(part, dict):
        return _append_mapping_part(content_parts, extracted_images, part)
    if adapter._is_pil_image(part):
        content_parts.append({"type": "image"})
        extracted_images.append(part)
        return 1
    content_parts.append({"type": "text", "text": str(part)})
    return 0


def _append_mapping_part(
    content_parts: list[dict[str, Any]],
    extracted_images: list[Any],
    part: dict[str, Any],
) -> int:
    """Append one mapping-style multimodal content part."""
    part_type = part.get("type")
    if part_type == "text":
        content_parts.append(part)
        return 0
    if part_type == "image_url":
        content_parts.append({"type": "image"})
        image_url = part.get("image_url", {}).get("url", "")
        if image_url:
            extracted_images.append(image_url)
        return 1
    if part_type == "image":
        content_parts.append({"type": "image"})
        extracted_images.append(_image_payload(part))
        return 1
    return 0


def _image_payload(part: dict[str, Any]) -> Any:
    """Return the usable image payload for one multimodal part."""
    return (
        part.get("data")
        or part.get("image")
        or part.get("path")
        or part.get("url")
        or part
    )


def _assistant_message(message: AIMessage) -> dict[str, Any]:
    """Return one chat-template assistant message.

    Tool calls are intentionally excluded — custom XML-format tool calls
    crash the Qwen HF chat template.  The workflow handles tool execution
    separately via force_response, so the template only needs plain text.
    """
    return {"role": "assistant", "content": message.content or ""}


def _tool_message(message: ToolMessage) -> dict[str, Any]:
    """Return one chat-template tool-result message."""
    return {
        "role": "tool",
        "content": message.content,
        "tool_call_id": getattr(message, "tool_call_id", ""),
    }
