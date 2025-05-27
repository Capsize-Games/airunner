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
    ), patch("airunner.handlers.llm.llm_model_manager.LocalAgent"), patch.object(
        LLMModelManager, "logger", new_callable=PropertyMock
    ) as mock_logger, patch.object(
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
        settings = SimpleNamespace(
            override_parameters=False,
            use_cache=True,
            model_version="v1",
            seed=42,
            random_seed=False,
        )
        mock_llm_settings.return_value = settings

        # Directly assign a mock agent with a mock chatbot property
        mock_chatbot_instance = MagicMock()
        mock_chatbot_instance.use_cache = True
        mock_chatbot_instance.model_version = "v1"
        mock_chatbot_instance.seed = 42
        mock_chatbot_instance.random_seed = False
        mock_agent = MagicMock()
        type(mock_agent).chatbot = PropertyMock(return_value=mock_chatbot_instance)

        mock_path_settings_instance = MagicMock()
        mock_path_settings_instance.base_path = "/tmp"
        mock_path_settings.return_value = mock_path_settings_instance
        mock_device.return_value = "cpu"
        mock_torch_dtype.return_value = None
        mock_attn_impl.return_value = None
        mock_adapter_path.return_value = "/tmp/adapter"
        manager = LLMModelManager()
        manager.api = MagicMock()
        manager._test_settings = settings
        manager._chat_agent = mock_agent  # Ensure chatbot property is always mocked
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
    llm_manager._unload_tokenizer = MagicMock(side_effect=AttributeError("fail"))
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
    ), patch("airunner.handlers.llm.llm_model_manager.torch.manual_seed") as tms, patch(
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


def test_is_mistral_and_llama_instruct(llm_manager):
    llm_manager._current_model_path = None
    assert not llm_manager.is_mistral
    assert not llm_manager.is_llama_instruct
    llm_manager._current_model_path = "/models/mistral-7b"
    assert llm_manager.is_mistral
    llm_manager._current_model_path = "/models/llama-2-instruct"
    assert llm_manager.is_llama_instruct
    llm_manager._current_model_path = "/models/llama-2"
    assert not llm_manager.is_llama_instruct


def test_use_cache_and_model_version(llm_manager):
    mock_chatbot = MagicMock()
    mock_chatbot.use_cache = True
    mock_chatbot.model_version = "v1"
    mock_chatbot.seed = 42
    mock_chatbot.random_seed = False
    mock_settings = SimpleNamespace(
        override_parameters=False,
        use_cache=True,
        model_version="v1",
        seed=42,
        random_seed=False,
    )
    with patch.object(
        type(llm_manager), "chatbot", new_callable=PropertyMock
    ) as mock_chatbot_prop, patch.object(
        type(llm_manager), "llm_generator_settings", new_callable=PropertyMock
    ) as mock_settings_prop:
        mock_chatbot_prop.return_value = mock_chatbot
        mock_settings_prop.return_value = mock_settings
        # override_parameters False: uses chatbot values
        mock_settings.override_parameters = False
        chatbot = llm_manager.chatbot
        assert hasattr(chatbot, "model_version")
        assert chatbot.model_version == "v1"
        assert llm_manager.use_cache is True
        # override_parameters True: uses llm_generator_settings values
        mock_settings.override_parameters = True
        mock_settings.model_version = "override-v2"
        mock_settings.use_cache = False
        assert llm_manager.model_version == "override-v2"
        assert llm_manager.use_cache is False


def test_model_path_expansion(llm_manager):
    # Should expanduser and join path
    path = llm_manager.model_path
    assert "llm" in path and "causallm" in path


def test_handle_request_calls_do_generate(llm_manager):
    llm_manager._do_set_seed = MagicMock()
    llm_manager.load = MagicMock()
    llm_manager._do_generate = MagicMock(return_value="resp")
    data = {
        "request_data": {
            "prompt": "hi",
            "action": LLMActionType.CHAT,
            "llm_request": MagicMock(),
        }
    }
    result = llm_manager.handle_request(data)
    llm_manager._do_set_seed.assert_called_once()
    llm_manager.load.assert_called_once()
    llm_manager._do_generate.assert_called_once()
    assert result == "resp"


def test_do_interrupt_and_on_conversation_deleted(llm_manager):
    # _chat_agent is None: should not error
    llm_manager._chat_agent = None
    llm_manager.do_interrupt()  # Should not raise
    llm_manager.on_conversation_deleted({})  # Should not raise
    # _chat_agent present: should call methods
    agent = MagicMock()
    llm_manager._chat_agent = agent
    llm_manager.do_interrupt()
    agent.interrupt_process.assert_called_once()
    llm_manager.on_conversation_deleted({"id": 1})
    agent.on_conversation_deleted.assert_called_once()


def test_clear_history_creates_and_updates(llm_manager):
    # _chat_agent is None: should not error
    llm_manager._chat_agent = None
    with patch(
        "airunner.handlers.llm.llm_model_manager.LLMGeneratorSettings"
    ) as mock_settings, patch(
        "airunner.handlers.llm.llm_model_manager.Conversation"
    ) as mock_conversation:
        mock_settings.objects.first.return_value = MagicMock(id=1)
        mock_conversation.objects.first.return_value = MagicMock(id=2)
        mock_conversation.create.return_value = MagicMock(id=3)
        llm_manager.clear_history()
        # Should update settings with new conversation id
        mock_settings.objects.update.assert_called()
    # _chat_agent present: should call clear_history
    agent = MagicMock()
    llm_manager._chat_agent = agent
    with patch(
        "airunner.handlers.llm.llm_model_manager.LLMGeneratorSettings"
    ) as mock_settings, patch(
        "airunner.handlers.llm.llm_model_manager.Conversation"
    ) as mock_conversation:
        mock_settings.objects.first.return_value = MagicMock(id=1)
        mock_conversation.objects.first.return_value = MagicMock(id=2)
        llm_manager.clear_history({"conversation_id": 2})
        agent.clear_history.assert_called_once()


def test_add_chatbot_response_to_history_and_load_conversation(llm_manager):
    # _chat_agent is None: should log warning
    llm_manager._chat_agent = None
    llm_manager.logger.warning = MagicMock()
    llm_manager.add_chatbot_response_to_history("msg")
    llm_manager.logger.warning.assert_called_with(
        "Cannot add response - chat agent not loaded"
    )
    llm_manager.load_conversation({"id": 1})
    assert llm_manager.logger.warning.call_count >= 2
    # _chat_agent present: should call methods
    agent = MagicMock()
    llm_manager._chat_agent = agent
    llm_manager.add_chatbot_response_to_history("msg2")
    agent.add_chatbot_response_to_history.assert_called_once_with("msg2")
    llm_manager.load_conversation({"id": 2})
    agent.on_load_conversation.assert_called_once()


def test_reload_rag_engine_and_on_section_changed(llm_manager):
    # _chat_agent is None: should log warning
    llm_manager._chat_agent = None
    llm_manager.logger.warning = MagicMock()
    llm_manager.reload_rag_engine()
    llm_manager.logger.warning.assert_called_with(
        "Cannot reload RAG engine - chat agent not loaded"
    )
    llm_manager.on_section_changed()
    llm_manager.logger.warning.assert_called_with(
        "Cannot update section - chat agent not loaded"
    )
    # _chat_agent present: should call methods
    agent = MagicMock()
    llm_manager._chat_agent = agent
    llm_manager.reload_rag_engine()
    agent.reload_rag_engine.assert_called_once()
    llm_manager.on_section_changed()
    assert agent.current_tab is None


def test_on_web_browser_page_html(llm_manager):
    # _chat_agent is None: should log error
    llm_manager._chat_agent = None
    llm_manager.logger.error = MagicMock()
    llm_manager.on_web_browser_page_html("<html></html>")
    llm_manager.logger.error.assert_called_with("Chat agent not loaded")
    # _chat_agent present: should call method
    agent = MagicMock()
    llm_manager._chat_agent = agent
    llm_manager.on_web_browser_page_html("<html>foo</html>")
    agent.on_web_browser_page_html.assert_called_once_with("<html>foo</html>")
