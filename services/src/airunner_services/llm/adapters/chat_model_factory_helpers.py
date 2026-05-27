"""Helper functions for ChatModelFactory settings resolution."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class LocalRuntimeConfig:
    """Resolved persisted runtime settings for local chat-model creation."""

    quantization_bits: int
    enable_thinking: bool
    reasoning_effort: str
    gguf_params: dict[str, Any]


def get_db_settings() -> Any:
    """Return persisted LLM generator settings when available."""
    from airunner_services.database.models.llm_generator_settings import (
        LLMGeneratorSettings,
    )

    return LLMGeneratorSettings.objects.first()


def _dtype_to_quantization_bits(dtype: Any) -> int:
    """Map one persisted dtype value to the legacy quantization selector."""
    mapping = {
        "2bit": 2,
        "4bit": 4,
        "8bit": 8,
    }
    return mapping.get(str(dtype or "").strip().lower(), 0)


def get_quantization_bits(db_settings: Any) -> int:
    """Resolve quantization preference from persisted service settings."""
    if db_settings is None:
        return 0

    db_quant = getattr(db_settings, "quantization_bits", None)
    if db_quant is not None:
        try:
            return int(db_quant)
        except (TypeError, ValueError):
            pass

    return _dtype_to_quantization_bits(getattr(db_settings, "dtype", None))


def get_enable_thinking(
    db_settings: Any,
    llm_settings: Any,
) -> bool:
    """Resolve the effective thinking-mode setting."""
    if db_settings is not None and hasattr(db_settings, "enable_thinking"):
        db_value = getattr(db_settings, "enable_thinking", None)
        if db_value is not None:
            return db_value
    return getattr(llm_settings, "enable_thinking", True)


def get_reasoning_effort(
    db_settings: Any,
    llm_settings: Any,
) -> str:
    """Resolve the effective GPT-OSS reasoning-effort setting."""
    allowed = {"low", "medium", "high"}

    if db_settings is not None and hasattr(db_settings, "reasoning_effort"):
        db_value = str(
            getattr(db_settings, "reasoning_effort", "medium") or "medium"
        ).strip().lower()
        if db_value in allowed:
            return db_value

    ui_value = str(
        getattr(llm_settings, "reasoning_effort", "medium") or "medium"
    ).strip().lower()
    if ui_value in allowed:
        return ui_value

    return "medium"


def get_chatbot_params(
    chatbot: Any,
    *,
    local_mode: bool,
) -> dict[str, Any]:
    """Build generation kwargs from chatbot settings."""
    if not chatbot:
        return {}
    if local_mode:
        return {
            "max_new_tokens": getattr(chatbot, "max_new_tokens", 500),
            "temperature": getattr(chatbot, "temperature", 700) / 10000.0,
            "top_p": getattr(chatbot, "top_p", 900) / 1000.0,
            "top_k": getattr(chatbot, "top_k", 50),
            "repetition_penalty": getattr(
                chatbot,
                "repetition_penalty",
                115,
            )
            / 100.0,
            "do_sample": getattr(chatbot, "do_sample", True),
        }

    return {
        "max_tokens": getattr(chatbot, "max_new_tokens", 4096),
        "temperature": getattr(chatbot, "temperature", 700) / 10000.0,
        "top_p": getattr(chatbot, "top_p", 900) / 1000.0,
        "top_k": getattr(chatbot, "top_k", 20),
        "repeat_penalty": getattr(
            chatbot,
            "repetition_penalty",
            115,
        )
        / 100.0,
    }


def build_local_runtime_config(
    db_settings: Any,
    llm_settings: Any,
    chatbot: Any,
) -> LocalRuntimeConfig:
    """Return the resolved persisted runtime config for local/GGUF loads."""
    return LocalRuntimeConfig(
        quantization_bits=get_quantization_bits(db_settings),
        enable_thinking=get_enable_thinking(db_settings, llm_settings),
        reasoning_effort=get_reasoning_effort(db_settings, llm_settings),
        gguf_params=get_chatbot_params(chatbot, local_mode=False),
    )