"""
Test suite for LLMModelManager in airunner.handlers.llm.llm_model_manager.
Focus: Increase coverage of core logic, especially load/unload, agent, and error handling paths.
"""

import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from airunner.handlers.llm.llm_model_manager import LLMModelManager
from airunner.enums import ModelType, ModelStatus, LLMActionType
from llama_index.core.chat_engine.types import AgentChatResponse
from types import SimpleNamespace


@pytest.fixture
def llm_manager():
    # Patch all model/tokenizer/agent loading/unloading and property dependencies
    with patch("airunner.handlers.llm.llm_model_manager.AutoTokenizer"), patch(
        "airunner.handlers.llm.llm_model_manager.AutoModelForCausalLM"
    ), patch(
        "airunner.handlers.llm.llm_model_manager.LocalAgent"
    ), patch.object(
        LLMModelManager, "logger", new_callable=PropertyMock
    ) as mock_logger, patch.object(
        LLMModelManager, "chatbot", new_callable=PropertyMock
    ) as mock_chatbot, patch.object(
        LLMModelManager, "path_settings", new_callable=PropertyMock
    ) as mock_path_settings, patch.object(
        LLMModelManager, "device", new_callable=PropertyMock
    ) as mock_device, patch.object(
        LLMModelManager, "torch_dtype", new_callable=PropertyMock
    ) as mock_torch_dtype, patch.object(
        LLMModelManager, "attn_implementation", new_callable=PropertyMock
    ) as mock_attn_impl, patch.object(
        LLMModelManager, "adapter_path", new_callable=PropertyMock
    ) as mock_adapter_path, patch.object(
        LLMModelManager, "_load_tokenizer"
    ), patch.object(
        LLMModelManager, "_load_model"
    ), patch.object(
        LLMModelManager, "_load_agent"
    ), patch.object(
        LLMModelManager, "_unload_model"
    ), patch.object(
        LLMModelManager, "_unload_tokenizer"
    ), patch.object(
        LLMModelManager, "_unload_agent"
    ), patch.object(
        LLMModelManager, "llm_generator_settings", new_callable=PropertyMock
    ) as mock_llm_settings:
        mock_logger.return_value = MagicMock()
        # This is the settings object that will be returned by the llm_generator_settings property mock
        # and also assigned to _test_settings for direct manipulation in the test.
        settings = SimpleNamespace(
            override_parameters=False,  # Initial value, will be changed by the test
            use_cache=True,
            model_version="v1",
            seed=42,  # Initial value, will be changed by the test
            random_seed=False,  # Initial value, will be changed by the test
        )
        mock_llm_settings.return_value = (
            settings  # Configure the mock to return this specific object
        )

        mock_chatbot_instance = MagicMock()
        mock_chatbot_instance.use_cache = True
        mock_chatbot_instance.model_version = "v1"
        mock_chatbot_instance.seed = 42
        mock_chatbot_instance.random_seed = False
        mock_chatbot.return_value = mock_chatbot_instance
        mock_path_settings_instance = MagicMock()
        mock_path_settings_instance.base_path = "/tmp"
        mock_path_settings.return_value = mock_path_settings_instance
        mock_device.return_value = "cpu"
        mock_torch_dtype.return_value = None
        mock_attn_impl.return_value = None
        mock_adapter_path.return_value = "/tmp/adapter"
        manager = LLMModelManager()
        manager.api = MagicMock()
        manager._test_settings = (
            settings  # Assign the same settings object for test manipulation
        )
        return manager


@pytest.fixture
def llm_manager_real_settings():
    # Patch only the dependencies needed, do not patch llm_generator_settings
    with patch("airunner.handlers.llm.llm_model_manager.AutoTokenizer"), patch(
        "airunner.handlers.llm.llm_model_manager.AutoModelForCausalLM"
    ), patch.object(
        LLMModelManager, "logger", new_callable=PropertyMock
    ) as mock_logger, patch.object(
        LLMModelManager, "chatbot", new_callable=PropertyMock
    ) as mock_chatbot, patch.object(
        LLMModelManager, "path_settings", new_callable=PropertyMock
    ) as mock_path_settings, patch.object(
        LLMModelManager, "device", new_callable=PropertyMock
    ) as mock_device, patch.object(
        LLMModelManager, "torch_dtype", new_callable=PropertyMock
    ) as mock_torch_dtype, patch.object(
        LLMModelManager, "attn_implementation", new_callable=PropertyMock
    ) as mock_attn_impl, patch.object(
        LLMModelManager, "adapter_path", new_callable=PropertyMock
    ) as mock_adapter_path, patch.object(
        LLMModelManager, "llm_generator_settings", new_callable=PropertyMock
    ) as mock_llm_settings:
        mock_logger.return_value = MagicMock()
        mock_chatbot_instance = MagicMock()
        mock_chatbot_instance.use_cache = True
        mock_chatbot_instance.model_version = "v1"
        mock_chatbot_instance.seed = 42
        mock_chatbot_instance.random_seed = False
        mock_chatbot.return_value = mock_chatbot_instance
        mock_path_settings_instance = MagicMock()
        mock_path_settings_instance.base_path = "/tmp"
        mock_path_settings.return_value = mock_path_settings_instance
        mock_device.return_value = "cpu"
        mock_torch_dtype.return_value = None
        mock_attn_impl.return_value = None
        mock_adapter_path.return_value = "/tmp/adapter"
        real_settings = SimpleNamespace(
            override_parameters=True,
            seed=123,
            random_seed=False,
        )
        mock_llm_settings.return_value = real_settings
        manager = LLMModelManager()
        manager.api = MagicMock()
        return manager


def test_load_and_unload_sets_status(llm_manager):
    llm_manager._load_tokenizer = MagicMock()
    llm_manager._load_model = MagicMock()
    llm_manager._load_agent = MagicMock()
    llm_manager._update_model_status = MagicMock(
        side_effect=lambda: llm_manager.change_model_status(
            ModelType.LLM, ModelStatus.LOADED
        )
    )
    llm_manager.model_status[ModelType.LLM] = ModelStatus.UNLOADED
    llm_manager.load()
    assert llm_manager.model_status[ModelType.LLM] == ModelStatus.LOADED
    llm_manager._unload_model = MagicMock()
    llm_manager._unload_tokenizer = MagicMock()
    llm_manager._unload_agent = MagicMock()
    llm_manager.change_model_status = MagicMock()
    llm_manager.model_status[ModelType.LLM] = ModelStatus.LOADED
    llm_manager.unload()
    llm_manager._unload_model.assert_called_once()
    llm_manager._unload_tokenizer.assert_called_once()
    llm_manager._unload_agent.assert_called_once()


def test_do_generate_handles_missing_agent(llm_manager):
    # Patch load/unload to no-op to avoid recursion and real loading
    llm_manager.load = MagicMock()
    llm_manager.unload = MagicMock()
    llm_manager._chat_agent = None
    from airunner.handlers.llm.llm_request import LLMRequest

    resp = llm_manager._do_generate(
        prompt="hi",
        action=LLMActionType.CHAT,
        llm_request=LLMRequest(node_id="n1"),
    )
    assert resp.error == "Chat agent not loaded"
    assert resp.is_end_of_message


def test_do_generate_calls_chat_and_final_message(llm_manager):
    # Patch load/unload to no-op to avoid recursion and real loading
    llm_manager.load = MagicMock()
    llm_manager.unload = MagicMock()
    mock_agent = MagicMock()
    mock_response = AgentChatResponse(response="ok", metadata=None)
    mock_agent.chat.return_value = mock_response
    llm_manager._chat_agent = mock_agent
    llm_manager._send_final_message = MagicMock()
    from airunner.handlers.llm.llm_request import LLMRequest

    resp = llm_manager._do_generate(
        prompt="hi",
        action=LLMActionType.CHAT,
        llm_request=LLMRequest(node_id="n2"),
    )
    mock_agent.chat.assert_called_once()
    llm_manager._send_final_message.assert_called_once()
    assert resp == mock_response


def test_unload_handles_exceptions(llm_manager):
    llm_manager.model_status[ModelType.LLM] = ModelStatus.LOADED
    llm_manager._unload_model = MagicMock(side_effect=AttributeError("fail"))
    llm_manager._unload_tokenizer = MagicMock(
        side_effect=AttributeError("fail")
    )
    llm_manager._unload_agent = MagicMock(side_effect=AttributeError("fail"))
    llm_manager.change_model_status = MagicMock()
    try:
        llm_manager.unload()
    except Exception:
        pytest.fail("unload() should not raise even if components fail")


def test_do_set_seed_sets_seed(llm_manager):
    # Create a specific settings object for this test
    test_specific_settings = SimpleNamespace(
        override_parameters=True,
        seed=123,
        random_seed=False,
        # Add other attributes that llm_generator_settings might have, if any
        # For example, if it's expected to have use_cache, model_version, etc.
        # based on how LLMGeneratorSettings is defined or used.
        # If not, these can be omitted.
        use_cache=True,  # Assuming default or typical value
        model_version="v1",  # Assuming default or typical value
    )

    llm_manager._tokenizer = MagicMock()

    # Patch the 'llm_generator_settings' property directly on the instance for this test
    with patch.object(
        LLMModelManager,
        "llm_generator_settings",
        new_callable=PropertyMock,
        return_value=test_specific_settings,
    ), patch(
        "airunner.handlers.llm.llm_model_manager.torch.manual_seed"
    ) as tms, patch(
        "airunner.handlers.llm.llm_model_manager.torch.cuda.manual_seed"
    ) as tcms, patch(
        "airunner.handlers.llm.llm_model_manager.torch.cuda.manual_seed_all"
    ) as tcmsa, patch(
        "airunner.handlers.llm.llm_model_manager.random.seed"
    ) as rseed, patch(
        "airunner.handlers.llm.llm_model_manager.AIRUNNER_MAX_SEED", 999999
    ):

        llm_manager._do_set_seed()
        tms.assert_called_with(123)
        tcms.assert_called_with(123)
        tcmsa.assert_called_with(123)
        rseed.assert_called_with(123)
        assert llm_manager._tokenizer.seed == 123
