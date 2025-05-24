"""
Unit tests for airunner.utils.llm.strip_names_from_message.strip_names_from_message
"""

import pytest


def test_strip_names_from_message_bot():
    from airunner.utils import strip_names_from_message

    msg = "Bot: hello"
    user = "User"
    bot = "Bot"
    assert strip_names_from_message(msg, user, bot) == "hello"


def test_strip_names_from_message_user():
    from airunner.utils import strip_names_from_message

    msg = "User: hi"
    user = "User"
    bot = "Bot"
    assert strip_names_from_message(msg, user, bot) == "hi"


def test_strip_names_from_message_none():
    from airunner.utils import strip_names_from_message

    msg = "hello"
    user = "User"
    bot = "Bot"
    assert strip_names_from_message(msg, user, bot) == "hello"
