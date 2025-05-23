import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from airunner.handlers.llm.agent.agents.base import BaseAgent
from airunner.handlers.llm.agent.agents.base import LLMActionType


class DummySettings:
    bot_language = "EN"
    enabled = True
    summarize_after_n_turns = 3
    llm_perform_analysis = True
    use_chatbot_mood = True
    update_user_data_enabled = True
    update_mood_after_n_turns = 2
    perform_conversation_summary = True
    max_function_calls = 3  # Add this attribute for test_react_tool_agent


class DummyChatbot:
    use_datetime = True
    use_personality = True
    use_mood = True
    use_system_instructions = False
    use_guardrails = False
    use_backstory = False
    system_instructions = ""
    guardrails_prompt = ""
    backstory = ""
    bot_personality = "friendly"
    botname = "TestBot"


class DummyUser:
    username = "testuser"
    zipcode = "12345"
    location_display_name = "Testville"
    data = {}
    latitude = 0.0
    longitude = 0.0

    def save(self):
        pass


class DummyConversation:
    id = 1
    user_id = 1
    summary = "summary"
    value = [{"role": "user", "blocks": []}, {"role": "bot", "blocks": []}]
    bot_mood = "happy"
    last_analysis_time = None
    last_analyzed_message_id = 0
    last_updated_message_id = 0
    timestamp = "2025-05-23 12:00:00"
    user_data = []


class DummyTool:
    def call(self, **kwargs):
        return MagicMock(content="result")

    @classmethod
    def from_defaults(cls, *args, **kwargs):
        return cls()


class DummyEngine:
    memory = None

    @classmethod
    def from_defaults(cls, **kwargs):
        return cls()


class DummyChatEngineTool:
    @classmethod
    def from_defaults(cls, **kwargs):
        return DummyTool()


class DummyReActAgentTool:
    @classmethod
    def from_tools(cls, *args, **kwargs):
        return DummyTool()


@pytest.fixture
def agent(monkeypatch):
    # Only patch classes that are imported or used directly in BaseAgent
    monkeypatch.setattr(
        "airunner.handlers.llm.agent.agents.base.RefreshSimpleChatEngine",
        DummyEngine,
    )
    monkeypatch.setattr(
        "airunner.handlers.llm.agent.agents.base.ChatEngineTool",
        DummyChatEngineTool,
    )
    monkeypatch.setattr(
        "airunner.handlers.llm.agent.agents.base.FunctionTool", DummyTool
    )
    monkeypatch.setattr(
        "airunner.handlers.llm.agent.agents.base.ReActAgentTool",
        DummyReActAgentTool,
    )
    monkeypatch.setattr(
        "airunner.handlers.llm.agent.agents.base.DatabaseChatStore", MagicMock
    )
    monkeypatch.setattr(
        "airunner.handlers.llm.agent.agents.base.SimpleChatStore", MagicMock
    )
    # Patch ChatMemoryBuffer with MagicMock and add from_defaults
    chat_memory_mock = MagicMock()
    chat_memory_mock.from_defaults = MagicMock(return_value=MagicMock())
    monkeypatch.setattr(
        "airunner.handlers.llm.agent.agents.base.ChatMemoryBuffer",
        chat_memory_mock,
    )
    monkeypatch.setattr(
        "airunner.handlers.llm.agent.agents.base.ExternalConditionStoppingCriteria",
        MagicMock,
    )
    monkeypatch.setattr(
        "airunner.handlers.llm.agent.agents.base.HuggingFaceLLM", MagicMock
    )
    monkeypatch.setattr(
        "airunner.handlers.llm.agent.agents.base.Tab", MagicMock
    )
    # Construct agent and set all other dependencies directly
    a = BaseAgent()
    a._chatbot = DummyChatbot()
    a._user = DummyUser()
    a._conversation = DummyConversation()
    a.llm_settings = DummySettings()
    a.api = MagicMock()
    # Do NOT set weather_prompt, application_settings, logger, language_settings, rag_settings
    return a


def test_prompt_property(agent):
    agent.prompt = "test"
    assert agent.prompt == "test"


def test_language_property(agent):
    assert agent.language == "English"
    agent.language = "French"
    assert agent._language == "French"


def test_use_memory_property(agent):
    agent._use_memory = True
    assert agent.use_memory is True


def test_action_property(agent):
    agent.action = LLMActionType.CHAT
    assert agent.action == LLMActionType.CHAT


def test_chat_mode_enabled(agent):
    agent.action = LLMActionType.CHAT
    assert agent.chat_mode_enabled is True


def test_rag_mode_enabled(agent):
    agent.action = LLMActionType.PERFORM_RAG_SEARCH
    with patch.object(
        BaseAgent, "rag_settings", new_callable=PropertyMock
    ) as mock_rag:
        mock_rag.return_value = MagicMock(enabled=True)
        assert agent.rag_mode_enabled is True


def test_conversation_summaries(agent):
    with patch(
        "airunner.handlers.llm.agent.agents.base.Conversation.objects.order_by"
    ) as mock_order_by:
        dummy_convs = []
        for i in range(5):
            dummy_conv = MagicMock()
            dummy_conv.summary = "summary"
            dummy_conv.id = i
            dummy_convs.append(dummy_conv)
        mock_order_by.return_value = dummy_convs
        assert "Recent conversation summaries" in agent.conversation_summaries


def test_date_time_prompt(agent):
    assert "Current Date / time information" in agent.date_time_prompt


def test_personality_prompt(agent):
    assert "personality" in agent.personality_prompt


def test_mood_prompt(agent):
    assert "current mood" in agent.mood_prompt


def test_operating_system_prompt(agent):
    assert "Operating system information" in agent.operating_system_prompt


def test_speakers_prompt(agent):
    assert "User information" in agent.speakers_prompt


def test_conversation_summary_prompt(agent):
    assert "- Conversation summary" in agent.conversation_summary_prompt


def test_llm_request_property(agent):
    req = agent.llm_request
    assert req is not None


def test_llm_property(agent):
    agent.model = MagicMock()
    agent.tokenizer = MagicMock()
    llm = agent.llm
    assert llm is not None


def test_webpage_html_property(agent):
    agent.webpage_html = "html"
    assert agent.webpage_html == "html"


def test_current_tab_property(agent):
    agent._current_tab = None
    with patch("airunner.handlers.llm.agent.agents.base.Tab") as mock_tab:
        mock_tab.objects.filter_by_first.return_value = MagicMock()
        tab = agent.current_tab
        assert tab is not None


def test_do_summarize_conversation(agent):
    agent.llm_settings.summarize_after_n_turns = 1
    agent._conversation.summary = None
    agent._conversation.value = [{}] * 2
    assert agent.do_summarize_conversation is True


def test_user_property(agent):
    agent._user = None
    u = agent.user
    assert u is not None


def test_information_scraper_tool(agent):
    tool = agent.information_scraper_tool
    assert tool is not None


def test_store_user_tool(agent):
    tool = agent.store_user_tool
    assert tool is not None


def test_quit_application_tool(agent):
    tool = agent.quit_application_tool
    assert tool is not None


def test_toggle_text_to_speech_tool(agent):
    tool = agent.toggle_text_to_speech_tool
    assert tool is not None


def test_list_files_in_directory_tool(agent):
    tool = agent.list_files_in_directory_tool
    assert tool is not None


def test_open_image_from_path_tool(agent):
    tool = agent.open_image_from_path_tool
    assert tool is not None


def test_clear_canvas_tool(agent):
    tool = agent.clear_canvas_tool
    assert tool is not None


def test_clear_conversation_tool(agent):
    tool = agent.clear_conversation_tool
    assert tool is not None


def test_set_working_width_and_height(agent):
    tool = agent.set_working_width_and_height
    assert tool is not None


def test_generate_image_tool(agent):
    tool = agent.generate_image_tool
    assert tool is not None


def test_tools_property(agent, monkeypatch):
    # Patch the chat_engine property at the class level
    from unittest.mock import PropertyMock

    monkeypatch.setattr(
        type(agent), "chat_engine", PropertyMock(return_value=DummyEngine())
    )
    tools = agent.tools
    assert isinstance(tools, list)
    assert any(tools)


def test_react_tool_agent(agent, monkeypatch):
    # Patch the chat_engine property at the class level
    from unittest.mock import PropertyMock

    monkeypatch.setattr(
        type(agent), "chat_engine", PropertyMock(return_value=DummyEngine())
    )
    tool = agent.react_tool_agent
    assert tool is not None


def test_chat_engine(agent, monkeypatch):
    from unittest.mock import PropertyMock

    monkeypatch.setattr(
        type(agent), "chat_engine", PropertyMock(return_value=DummyEngine())
    )
    engine = agent.chat_engine
    assert engine is not None


def test_mood_engine_tool(agent, monkeypatch):
    from unittest.mock import PropertyMock

    monkeypatch.setattr(
        type(agent), "chat_engine", PropertyMock(return_value=DummyEngine())
    )
    tool = agent.mood_engine_tool
    assert tool is not None


def test_streaming_stopping_criteria(agent):
    crit = agent.streaming_stopping_criteria
    assert crit is not None


def test_chat_engine(agent):
    engine = agent.chat_engine
    assert engine is not None


def test_update_user_data_engine(agent):
    engine = agent.update_user_data_engine
    assert engine is not None


def test_mood_engine(agent):
    engine = agent.mood_engine
    assert engine is not None


def test_summary_engine(agent):
    engine = agent.summary_engine
    assert engine is not None


def test_information_scraper_engine(agent):
    engine = agent.information_scraper_engine
    assert engine is not None


def test_mood_engine_tool(agent):
    tool = agent.mood_engine_tool
    assert tool is not None


def test_update_user_data_tool(agent):
    tool = agent.update_user_data_tool
    assert tool is not None


def test_summary_engine_tool(agent):
    tool = agent.summary_engine_tool
    assert tool is not None


def test_chat_engine_tool(agent):
    tool = agent.chat_engine_tool
    assert tool is not None


def test_chat_engine_react_tool(agent):
    tool = agent.chat_engine_react_tool
    assert tool is not None


def test_do_interrupt_property(agent):
    agent.do_interrupt = True
    assert agent.do_interrupt is True


def test_bot_mood_property(agent):
    agent._conversation.bot_mood = ""
    assert agent.bot_mood == "neutral"
    agent._conversation.bot_mood = "happy"
    assert agent.bot_mood == "happy"


def test_conversation_property(agent):
    agent._conversation = None
    agent._use_memory = True
    c = agent.conversation
    assert c is not None


def test_conversation_id_property(agent):
    agent._conversation_id = None
    agent._conversation = DummyConversation()
    cid = agent.conversation_id
    assert cid == 1


def test_bot_personality_property(agent):
    assert agent.bot_personality == "friendly"


def test_botname_property(agent):
    assert agent.botname == "TestBot"


def test_username_property(agent):
    assert agent.username == "testuser"


def test_zipcode_property(agent):
    assert agent.zipcode == "12345"


def test_location_display_name_property(agent):
    agent.location_display_name = "NewName"
    assert agent.user.location_display_name == "NewName"


def test_day_of_week_property(agent):
    assert isinstance(agent.day_of_week, str)


def test_current_date_property(agent):
    assert isinstance(agent.current_date, str)


def test_current_time_property(agent):
    assert isinstance(agent.current_time, str)


def test_timezone_property(agent):
    assert isinstance(agent.timezone, str)


def test_information_scraper_prompt(agent):
    assert "information scraper" in agent._information_scraper_prompt


def test_summarize_conversation_prompt(agent):
    assert "summary writer" in agent._summarize_conversation_prompt


def test_mood_update_prompt(agent):
    assert "mood analyzier" in agent._mood_update_prompt


def test_system_prompt(agent):
    assert "Your name is" in agent.system_prompt


def test_update_user_data_prompt(agent):
    assert "examine the conversation" in agent._update_user_data_prompt


def test_react_agent_prompt(agent):
    assert agent.system_prompt in agent.react_agent_prompt


def test_chat_store_property(agent):
    store = agent.chat_store
    assert store is not None


def test_chat_memory_property(agent):
    mem = agent.chat_memory
    assert mem is not None


def test_unload(agent):
    agent._llm = MagicMock()
    agent.model = MagicMock()
    agent.tokenizer = MagicMock()
    agent._chat_engine = MagicMock()
    agent._chat_engine_tool = MagicMock()
    agent._react_tool_agent = MagicMock()
    agent.unload()
    assert agent.model is None
    assert agent.tokenizer is None
    assert agent._llm is None
    assert agent._chat_engine is None
    assert agent._chat_engine_tool is None
    assert agent._react_tool_agent is None
