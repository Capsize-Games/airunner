import pytest
from unittest.mock import MagicMock
from airunner.gui.windows.main.conversation_manager import ConversationManager


class DummyMainWindow:
    def __init__(self):
        self.prompt = "test"
        self.negative_prompt = "neg"
        self.api = MagicMock()


def test_clear_all_prompts():
    mw = DummyMainWindow()
    cm = ConversationManager(mw.api)
    cm.clear_all_prompts(mw)
    assert mw.prompt == ""
    assert mw.negative_prompt == ""
    mw.api.clear_prompts.assert_called_once()


def test_create_saved_prompt_logs():
    mw = DummyMainWindow()
    logger = MagicMock()
    cm = ConversationManager(mw.api, logger=logger)
    data = {"prompt": "foo"}
    cm.create_saved_prompt(mw, data)
    logger.info.assert_called_with(f"Saving prompt: {data}")
