"""Helper functions for ChatModelFactory settings resolution."""

from __future__ import annotations

from typing import Any


def get_db_settings() -> Any:
    """Return persisted LLM generator settings when available."""
    from airunner_model.models.llm_generator_settings import (
        LLMGeneratorSettings,
    )

    return LLMGeneratorSettings.objects.first()


def get_quantization_bits(db_settings: Any) -> int:
    """Resolve quantization preference from UI settings and the database."""
    from airunner.utils.settings.get_qsettings import get_qsettings

    quantization_bits = 0
    try:
        qsettings = get_qsettings()
        saved = qsettings.value("llm_settings/quantization_bits", None)
        if saved is not None:
            quantization_bits = int(saved)
    except Exception:
        pass

    if db_settings is not None:
        db_quant = getattr(db_settings, "quantization_bits", None)
        if db_quant is not None:
            quantization_bits = db_quant
    return quantization_bits


def get_enable_thinking(
    db_settings: Any,
    llm_settings: Any,
) -> bool:
    """Resolve the effective thinking-mode setting."""
    _ = (db_settings, llm_settings)
    return True


def get_reasoning_effort(
    db_settings: Any,
    llm_settings: Any,
) -> str:
    """Resolve the effective reasoning-effort setting.

    AIRunner now treats maximum reasoning effort as the global runtime
    default. Adapters that do not support reasoning-effort levels can
    ignore this value safely.
    """
    _ = (db_settings, llm_settings)
    return "high"


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