"""Tests for local ChatModelFactory execution ownership."""

from types import SimpleNamespace
from unittest.mock import patch, sentinel

from airunner.components.llm.adapters.chat_model_factory import ChatModelFactory


def test_create_from_settings_loads_local_components_on_demand():
    """Local chat models should be buildable without preloaded manager state."""
    llm_settings = SimpleNamespace(use_local_llm=True, enable_thinking=True)

    with patch(
        "airunner.utils.settings.get_qsettings.get_qsettings"
    ) as mock_qsettings, patch(
        "airunner.components.llm.data.llm_generator_settings.LLMGeneratorSettings"
    ) as mock_db_settings, patch.object(
        ChatModelFactory,
        "_load_local_execution_components",
        return_value=(sentinel.model, sentinel.tokenizer),
    ) as mock_load_components, patch.object(
        ChatModelFactory,
        "create_local_model",
        return_value="chat-model",
    ) as mock_create_local:
        mock_qsettings.return_value.value.return_value = None
        mock_db_settings.objects.first.return_value = SimpleNamespace(
            model_id=None,
            quantization_bits=4,
            enable_thinking=True,
        )

        result = ChatModelFactory.create_from_settings(
            llm_settings=llm_settings,
            model_path="/tmp/model",
        )

    assert result == "chat-model"
    mock_load_components.assert_called_once_with(
        llm_settings=llm_settings,
        model_path="/tmp/model",
    )
    mock_create_local.assert_called_once()


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
    ) as mock_create_ollama, patch.object(
        ChatModelFactory,
        "_load_local_execution_components",
    ) as mock_load_components:
        mock_qsettings.return_value.value.return_value = None
        mock_db_settings.objects.first.return_value = None

        result = ChatModelFactory.create_from_settings(
            llm_settings=llm_settings,
            model_path="/tmp/model",
        )

    assert result == "ollama-model"
    mock_load_components.assert_not_called()
    mock_create_ollama.assert_called_once_with(
        model_name="qwen2.5",
        base_url="http://localhost:11434",
        temperature=0.7,
    )