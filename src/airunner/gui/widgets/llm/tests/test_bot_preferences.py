"""
Test suite for bot_preferences.py in LLM widgets.
"""

import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from airunner.gui.widgets.llm import bot_preferences


@pytest.fixture
def bot_prefs_widget(qtbot):
    widget = bot_preferences.BotPreferencesWidget()
    qtbot.addWidget(widget)
    widget.show()

    # Patch the 'chatbot' property to return a mock with required string properties
    chatbot = MagicMock()
    chatbot.name = "dummy"
    chatbot.botname = "dummy"
    chatbot.bot_personality = "personality"
    chatbot.assign_names = False
    chatbot.use_personality = False
    chatbot.system_instructions = "sys"
    chatbot.use_system_instructions = False
    chatbot.guardrails_prompt = "guard"
    chatbot.use_guardrails = False
    chatbot.use_weather_prompt = False
    chatbot.use_datetime = False
    chatbot.gender = "Male"
    chatbot.target_files = []
    chatbot.voice_id = None

    # Patch the 'chatbot' property on the instance's type
    patcher_chatbot = patch.object(
        type(widget), "chatbot", new_callable=PropertyMock
    )
    mock_chatbot_prop = patcher_chatbot.start()
    mock_chatbot_prop.return_value = chatbot

    # Patch the 'chatbots' property on the instance's type
    patcher_chatbots = patch.object(
        type(widget), "chatbots", new_callable=PropertyMock
    )
    mock_chatbots_prop = patcher_chatbots.start()
    mock_chatbots_prop.return_value = [chatbot]

    # Patch the 'logger' property on the instance's type
    patcher_logger = patch.object(
        type(widget), "logger", new_callable=PropertyMock
    )
    mock_logger_prop = patcher_logger.start()
    mock_logger_prop.return_value = MagicMock()

    # Patch any other required attributes
    widget.api = MagicMock()

    # Ensure patchers are stopped after the test
    def fin():
        patcher_chatbot.stop()
        patcher_chatbots.stop()
        patcher_logger.stop()

    pytest.fixture(autouse=True)(fin)

    return widget


def test_bot_preferences_widget_constructs(bot_prefs_widget):
    assert bot_prefs_widget is not None


def test_load_form_elements_runs(bot_prefs_widget):
    # Should not raise even if chatbot is a MagicMock
    bot_prefs_widget.load_form_elements()
