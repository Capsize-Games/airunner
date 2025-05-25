"""
Regression test for Conversation.create() and Conversation manager methods.
Ensures that all returned objects are dataclasses and not ORM objects, preventing DetachedInstanceError.
"""

import pytest
from airunner.data.models.conversation import Conversation
from airunner.data.models.user import User
from airunner.data.models.chatbot import Chatbot
from airunner.data.session_manager import session_scope


@pytest.fixture(autouse=True)
def clean_conversations():
    with session_scope() as session:
        session.query(Conversation).delete()
        session.query(User).delete()
        session.query(Chatbot).delete()
        session.commit()
    yield
    with session_scope() as session:
        session.query(Conversation).delete()
        session.query(User).delete()
        session.query(Chatbot).delete()
        session.commit()


def test_conversation_create_returns_dataclass():
    user = User.objects.create(username="TestUser")
    chatbot = Chatbot.objects.create(botname="TestBot")
    conversation = Conversation.create(chatbot=chatbot, user=user)
    assert conversation is not None
    assert hasattr(conversation, "bot_mood")
    assert conversation.__class__.__name__.endswith("Data")
    # Should not raise DetachedInstanceError
    _ = conversation.bot_mood


def test_conversation_manager_methods_return_dataclass():
    user = User.objects.create(username="TestUser2")
    chatbot = Chatbot.objects.create(botname="TestBot2")
    Conversation.create(chatbot=chatbot, user=user)
    got = Conversation.objects.first()
    assert got is not None
    assert hasattr(got, "bot_mood")
    assert got.__class__.__name__.endswith("Data")
    _ = got.bot_mood
    all_convs = Conversation.objects.all()
    assert all_convs
    for c in all_convs:
        assert c.__class__.__name__.endswith("Data")
        _ = c.bot_mood
