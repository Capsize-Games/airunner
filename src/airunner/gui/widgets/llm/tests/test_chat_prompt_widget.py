"""
Test suite for chat_prompt_widget.py in LLM widgets.
"""

import pytest

pytest.skip(
    "ChatPromptWidget launches a GUI and is not suitable for headless CI. Skipped by default.",
    allow_module_level=True,
)

import sys
from unittest.mock import patch
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
