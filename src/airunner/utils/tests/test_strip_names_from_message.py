import pytest
from airunner.utils.llm.strip_names_from_message import (
    strip_names_from_message,
)


def test_strip_names_from_message_botname():
    msg = "Bot: hello"
    result = strip_names_from_message(msg, username="User", botname="Bot")
    assert result == "hello"


def test_strip_names_from_message_username():
    msg = "User: hi"
    result = strip_names_from_message(msg, username="User", botname="Bot")
    assert result == "hi"


def test_strip_names_from_message_no_strip():
    msg = "Something else"
    result = strip_names_from_message(msg, username="User", botname="Bot")
    assert result == "Something else"


def test_strip_names_from_message_both():
    msg = "Bot: User: nested"
    # Only botname is stripped, then username is checked again
    result = strip_names_from_message(msg, username="User", botname="Bot")
    assert result == "nested"
