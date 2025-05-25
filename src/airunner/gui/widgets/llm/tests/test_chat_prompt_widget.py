"""
Test suite for chat_prompt_widget.py in LLM widgets.
"""

import pytest

# Remove or comment out the module-level skip to allow tests to run
# pytest.skip(
#     "ChatPromptWidget launches a GUI and is not suitable for headless CI. Skipped by default.",
#     allow_module_level=True,
# )

import sys
from unittest.mock import patch, MagicMock, PropertyMock
from airunner.gui.widgets.llm import chat_prompt_widget


@pytest.fixture
def chat_prompt(qtbot):
    # Patch sys.exit and QApplication.exec to prevent app launch
    with patch("sys.exit"), patch(
        "PySide6.QtWidgets.QApplication.exec", return_value=None
    ):
        widget = chat_prompt_widget.ChatPromptWidget()
        qtbot.addWidget(widget)
        widget.show()
        yield widget
        widget.close()


def test_chat_prompt_widget_constructs(chat_prompt):
    assert chat_prompt is not None


def test_clear_prompt_runs(chat_prompt):
    chat_prompt.clear_prompt()


def test_prompt_text_changed_runs(chat_prompt):
    chat_prompt.prompt_text_changed()


def test_do_generate_sends_prompt(chat_prompt, qtbot):
    # Arrange: Patch user, chatbot, and llm_generator_settings properties to return mocks
    with patch.object(
        type(chat_prompt), "user", new_callable=PropertyMock
    ) as mock_user_prop, patch.object(
        type(chat_prompt), "chatbot", new_callable=PropertyMock
    ) as mock_chatbot_prop, patch.object(
        type(chat_prompt), "llm_generator_settings", new_callable=PropertyMock
    ) as mock_llm_settings_prop:
        mock_user = MagicMock()
        mock_user.username = "test_user"
        mock_user_prop.return_value = mock_user
        mock_chatbot = MagicMock()
        mock_chatbot.botname = "test_bot"
        mock_chatbot_prop.return_value = mock_chatbot
        mock_llm_settings = MagicMock()
        mock_llm_settings.action = "CHAT"
        mock_llm_settings_prop.return_value = mock_llm_settings
        chat_prompt.api = MagicMock()
        chat_prompt.api.llm.send_request = MagicMock()
        chat_prompt.prompt = "Hello, world!"
        chat_prompt.generating = False

        # Patch methods that interact with the UI or are side effects
        with patch.object(
            chat_prompt,
            "add_message_to_conversation",
            return_value=MagicMock(),
        ) as add_msg, patch.object(
            chat_prompt, "clear_prompt"
        ) as clear_prompt, patch.object(
            chat_prompt, "start_progress_bar"
        ) as start_progress:
            chat_prompt.do_generate()

        # Assert: send_request should be called with the prompt
        chat_prompt.api.llm.send_request.assert_called()
        clear_prompt.assert_called_once()
        start_progress.assert_called_once()
        add_msg.assert_called_once()
