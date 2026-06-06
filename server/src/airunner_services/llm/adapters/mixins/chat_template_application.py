"""Helpers for applying HuggingFace chat templates."""

from __future__ import annotations

import os
from typing import Any

from airunner_services.database.models.llm_generator_settings import (
    LLMGeneratorSettings,
)
from airunner_services.llm.adapters.mixins.chat_template_message_builder import (
    ChatTemplatePayload,
)


def apply_chat_template(
    adapter: Any,
    messages: list[Any],
    payload: ChatTemplatePayload,
) -> str:
    """Apply the best available chat template for one prompt."""
    log_chat_template_preview(adapter, payload.chat_messages)
    replace_missing_image_placeholders(adapter, payload)
    template_kwargs = build_template_kwargs(adapter)
    store_pending_images(adapter, payload.extracted_images)
    template_target = resolve_template_target(adapter)
    if template_target is None:
        return adapter._fallback_format(messages)
    return apply_template_with_fallback(
        adapter,
        template_target,
        payload.chat_messages,
        template_kwargs,
        messages,
    )


def log_chat_template_preview(
    adapter: Any,
    chat_messages: list[dict[str, Any]],
) -> None:
    """Log a redacted preview of template input when explicitly enabled."""
    if os.environ.get("AIRUNNER_LOG_SENSITIVE_PROMPTS") != "1":
        return
    try:
        preview = [_message_preview(message) for message in chat_messages[:5]]
        adapter.logger.debug(
            "Chat template input message preview (redacted): %s",
            preview,
        )
    except Exception:
        return


def _message_preview(message: dict[str, Any]) -> dict[str, Any]:
    """Return one redacted preview entry for a chat-template message."""
    content = message.get("content", "")
    if isinstance(content, list):
        content_len = sum(_content_part_length(part) for part in content)
    else:
        content_len = len(str(content))
    return {"role": message.get("role"), "content_len": content_len}


def _content_part_length(part: Any) -> int:
    """Return one safe content-length estimate for a message part."""
    if isinstance(part, dict):
        return len(str(part.get("text", "")))
    return len(str(part))


def replace_missing_image_placeholders(
    adapter: Any,
    payload: ChatTemplatePayload,
) -> None:
    """Replace empty image placeholders with text when extraction failed."""
    if payload.image_placeholders <= 0 or payload.extracted_images:
        return
    try:
        for message in payload.chat_messages:
            _replace_message_images(message)
        adapter.logger.warning(
            "Image placeholders found but no images extracted; replaced "
            "with text fallback"
        )
    except Exception:
        return


def _replace_message_images(message: dict[str, Any]) -> None:
    """Replace image parts in one message with unavailable markers."""
    content = message.get("content", [])
    if not isinstance(content, list):
        return
    for index, part in enumerate(content):
        if isinstance(part, dict) and part.get("type") == "image":
            content[index] = {
                "type": "text",
                "text": "[image unavailable]",
            }


def build_template_kwargs(adapter: Any) -> dict[str, Any]:
    """Build chat-template keyword arguments for one request."""
    template_kwargs = {
        "tokenize": False,
        "add_generation_prompt": True,
    }
    template_kwargs.update(_tool_template_kwargs(adapter))
    template_kwargs.update(_thinking_template_kwargs(adapter))
    return template_kwargs


def _tool_template_kwargs(adapter: Any) -> dict[str, Any]:
    """Return chat-template tool kwargs when JSON mode uses bound tools."""
    if not hasattr(adapter, "tools") or not adapter.tools:
        return {}
    if getattr(adapter, "tool_calling_mode", None) != "json":
        return {}
    return {"tools": adapter.tools}


def _thinking_template_kwargs(adapter: Any) -> dict[str, Any]:
    """Return thinking-mode kwargs for one supported model."""
    if not adapter._check_model_supports_thinking():
        return {}
    return {"enable_thinking": resolve_thinking_preference(adapter)}


def resolve_thinking_preference(adapter: Any) -> bool:
    """Resolve the effective thinking-mode preference for one request."""
    instance_value = getattr(adapter, "enable_thinking", None)
    if instance_value is not None:
        adapter.logger.debug(
            "[THINKING] enable_thinking=%s (from instance attr)",
            instance_value,
        )
        return instance_value
    db_settings = LLMGeneratorSettings.objects.first()
    user_value = True
    if db_settings is not None and db_settings.enable_thinking is not None:
        user_value = db_settings.enable_thinking
    adapter.logger.debug(
        "[THINKING] enable_thinking=%s (from DB setting)",
        user_value,
    )
    return user_value


def store_pending_images(adapter: Any, extracted_images: list[Any]) -> None:
    """Persist extracted images for downstream vision processing."""
    adapter._pending_images = list(extracted_images)
    if extracted_images:
        adapter.logger.info(
            "Stored %s images for vision processing",
            len(extracted_images),
        )


def resolve_template_target(adapter: Any) -> Any | None:
    """Resolve the best chat-template target for one adapter."""
    if (
        getattr(adapter, "is_vision_model", False)
        and getattr(adapter, "processor", None) is not None
        and hasattr(adapter.processor, "apply_chat_template")
    ):
        return adapter.processor
    if adapter.tokenizer and hasattr(adapter.tokenizer, "apply_chat_template"):
        return adapter.tokenizer
    return None


def apply_template_with_fallback(
    adapter: Any,
    template_target: Any,
    chat_messages: list[dict[str, Any]],
    template_kwargs: dict[str, Any],
    messages: list[Any],
) -> str:
    """Apply one chat template and fall back safely on failure."""
    try:
        return template_target.apply_chat_template(
            chat_messages,
            **template_kwargs,
        )
    except Exception:
        return _retry_template_with_fallback(
            adapter,
            template_target,
            chat_messages,
            template_kwargs,
            messages,
        )


def _retry_template_with_fallback(
    adapter: Any,
    template_target: Any,
    chat_messages: list[dict[str, Any]],
    template_kwargs: dict[str, Any],
    messages: list[Any],
) -> str:
    """Retry template application with tokenizer fallback when possible."""
    if not _can_retry_with_tokenizer(adapter, template_target):
        return adapter._fallback_format(messages)
    try:
        return adapter.tokenizer.apply_chat_template(
            chat_messages,
            **template_kwargs,
        )
    except Exception:
        return adapter._fallback_format(messages)


def _can_retry_with_tokenizer(adapter: Any, template_target: Any) -> bool:
    """Return True when tokenizer fallback is available."""
    return bool(
        template_target is not adapter.tokenizer
        and adapter.tokenizer
        and hasattr(adapter.tokenizer, "apply_chat_template")
    )
