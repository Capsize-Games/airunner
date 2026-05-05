"""Tests for local ChatModelFactory execution ownership."""

from types import SimpleNamespace
from unittest.mock import patch

import pytest

from airunner.components.llm.adapters.chat_model_factory import ChatModelFactory


def test_create_from_settings_rejects_non_gguf_local_execution():
    """Local execution must stay on the GGUF llama.cpp path."""
    llm_settings = SimpleNamespace(use_local_llm=True, enable_thinking=True)

    with patch(
        "airunner.utils.settings.get_qsettings.get_qsettings"
    ) as mock_qsettings, patch(
        "airunner.components.llm.data.llm_generator_settings.LLMGeneratorSettings"
    ) as mock_db_settings:
        mock_qsettings.return_value.value.return_value = None
        mock_db_settings.objects.first.return_value = SimpleNamespace(
            model_id=None,
            quantization_bits=4,
            enable_thinking=True,
        )

        with pytest.raises(ValueError) as exc_info:
            ChatModelFactory.create_from_settings(
                llm_settings=llm_settings,
                model_path="/tmp/model",
            )

    assert "llama.cpp" in str(exc_info.value)


def test_create_from_settings_keeps_ollama_provider_routing():
    """Non-local provider routing should stay on the existing factory path."""
    llm_settings = SimpleNamespace(
        use_local_llm=False,
        use_ollama=True,
        use_openrouter=False,
        use_openai=False,
        ollama_model="qwen2.5",
        ollama_base_url="http://localhost:11434",
    )

    with patch(
        "airunner.utils.settings.get_qsettings.get_qsettings"
    ) as mock_qsettings, patch(
        "airunner.components.llm.data.llm_generator_settings.LLMGeneratorSettings"
    ) as mock_db_settings, patch.object(
        ChatModelFactory,
        "create_ollama_model",
        return_value="ollama-model",
    ) as mock_create_ollama:
        mock_qsettings.return_value.value.return_value = None
        mock_db_settings.objects.first.return_value = None

        result = ChatModelFactory.create_from_settings(
            llm_settings=llm_settings,
            model_path="/tmp/model",
        )

    assert result == "ollama-model"
    mock_create_ollama.assert_called_once_with(
        model_name="qwen2.5",
        base_url="http://localhost:11434",
        temperature=0.7,
    )


def test_create_from_settings_passes_reasoning_effort_to_gguf_model():
    """GPT-OSS runtime config should flow into GGUF model creation."""
    llm_settings = SimpleNamespace(
        use_local_llm=True,
        enable_thinking=True,
        reasoning_effort="high",
    )
    db_settings = SimpleNamespace(
        model_id="gpt-oss-20b",
        quantization_bits=0,
        enable_thinking=True,
        reasoning_effort="low",
    )
    optimizer = SimpleNamespace(
        find_existing_gguf=lambda *_args, **_kwargs: None,
        bits_to_gguf_quantization=lambda *_args, **_kwargs: "Q4_K_M",
        ensure_gguf=lambda *_args, **_kwargs: None,
    )

    with patch(
        "airunner.components.llm.adapters.chat_model_factory.get_db_settings",
        return_value=db_settings,
    ), patch(
        "airunner.components.llm.adapters.chat_model_factory.get_quantization_bits",
        return_value=0,
    ), patch(
        "airunner.components.llm.adapters.chat_model_factory.get_model_optimizer",
        return_value=optimizer,
    ), patch.object(
        ChatModelFactory,
        "create_gguf_model",
        return_value="gguf-model",
    ) as mock_create_gguf:
        result = ChatModelFactory.create_from_settings(
            llm_settings=llm_settings,
            model_path="/tmp/gpt-oss-20b-F16.gguf",
        )

    assert result == "gguf-model"
    assert mock_create_gguf.call_args.kwargs["reasoning_effort"] == "low"
    assert mock_create_gguf.call_args.kwargs["tool_calling_mode"] == "react"