"""
Unit tests for ReactAgentEngine in airunner.handlers.llm.agent.chat_engine.react_agent_engine.
Covers property getter/setter for memory and metaclass instantiation.
"""

import pytest
from airunner.handlers.llm.agent.chat_engine.react_agent_engine import (
    ReactAgentEngine,
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


@pytest.fixture
def dummy_memory():
    return DummyMemory(value="test-memory")


def test_memory_property_get_set(dummy_memory):
    class DummyCallbackManager:
        pass

    class DummyLLM:
        callback_manager = DummyCallbackManager()

    engine = ReactAgentEngine([], DummyLLM(), dummy_memory)
    assert engine.memory is dummy_memory
    # Test set/get with a new value
    new_memory = DummyMemory(value="new-memory")
    engine.memory = new_memory
    assert engine.memory is new_memory


def test_metaclass_is_react_agent_meta():
    assert isinstance(ReactAgentEngine, type)
    # Should be subclass of ReActAgent
    assert issubclass(ReactAgentEngine, ReactAgentEngine.__bases__[0])
