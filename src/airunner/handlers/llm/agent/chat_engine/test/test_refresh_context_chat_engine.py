"""
Unit tests for RefreshContextChatEngine in airunner.handlers.llm.agent.chat_engine.refresh_context_chat_engine.
Covers property getter/setter for memory, llm, and update_system_prompt logic.
"""

import pytest
from airunner.handlers.llm.agent.chat_engine.refresh_context_chat_engine import (
    RefreshContextChatEngine,
)
from llama_index.core.memory import BaseMemory


class DummyMemory(BaseMemory):
    value: str = None

    def __init__(self, value=None):
        super().__init__()
        self.value = value

    def get(self):
        return self.value

    def set(self, value):
        self.value = value

    @classmethod
    def from_defaults(cls, *args, **kwargs):
        return cls()

    def get_all(self):
        return []

    def put(self, *args, **kwargs):
        pass

    def reset(self):
        self.value = None


class DummyLLM:
    class metadata:
        system_role = "system"


@pytest.fixture
def dummy_memory():
    return DummyMemory(value="test-memory")


@pytest.fixture
def dummy_llm():
    return DummyLLM()


def test_memory_property_get_set(dummy_memory, dummy_llm):
    engine = RefreshContextChatEngine.__new__(RefreshContextChatEngine)
    engine._llm = dummy_llm
    engine._memory = dummy_memory
    assert engine.memory is dummy_memory
    new_memory = DummyMemory(value="new-memory")
    engine.memory = new_memory
    assert engine.memory is new_memory


def test_llm_property(dummy_llm):
    engine = RefreshContextChatEngine.__new__(RefreshContextChatEngine)
    engine._llm = dummy_llm
    assert engine.llm is dummy_llm


def test_update_system_prompt_sets_prefix(dummy_llm):
    engine = RefreshContextChatEngine.__new__(RefreshContextChatEngine)
    engine._llm = dummy_llm
    engine._prefix_messages = []
    engine.update_system_prompt("hello world")
    assert len(engine._prefix_messages) == 1
    assert engine._prefix_messages[0].content == "hello world"
    assert engine._prefix_messages[0].role == "system"


def test_update_system_prompt_overwrites_prefix(dummy_llm):
    engine = RefreshContextChatEngine.__new__(RefreshContextChatEngine)
    engine._llm = dummy_llm

    class DummyMsg:
        def __init__(self, content, role):
            self.content = content
            self.role = role

    engine._prefix_messages = [DummyMsg("old", "system")]
    engine.update_system_prompt("new prompt")
    assert len(engine._prefix_messages) == 1
    assert engine._prefix_messages[0].content == "new prompt"
    assert engine._prefix_messages[0].role == "system"
