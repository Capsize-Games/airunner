"""Tests for dynamic mood integration into system prompt.

Ensures that after a hostile user message the WorkflowManager's system prompt
contains the frustrated mood before building the prompt for generation.

Uses a lightweight fake chatbot/settings to avoid loading heavy models.
"""

from airunner.components.llm.managers.workflow_manager import WorkflowManager


class FakeSettings:
    def __init__(self):
        self.use_chatbot_mood = True
        self.update_mood_after_n_turns = 1  # Update every turn for test


class FakeChatbot:
    def __init__(self):
        self.botname = "Computer"
        self.personality = None
        self.use_mood = True


class DummyChatModel:
    """Minimal stand-in for a LangChain ChatModel with invoke/stream signatures."""

    def __init__(self):
        self._messages = []

    def invoke(self, messages, config=None):
        # Return a dict mimicking workflow result
        return {"messages": self._messages + messages["messages"]}


# We cannot compile full LangGraph workflow here; instead we test system_prompt property logic.


def test_system_prompt_reflects_frustrated_mood():
    settings = FakeSettings()
    chatbot = FakeChatbot()
    # Create WorkflowManager with minimal dependencies
    wm = WorkflowManager(
        system_prompt="initial",  # will be replaced
        chat_model=DummyChatModel(),
        tools=[],
        llm_settings=settings,
        chatbot=chatbot,
        signal_emitter=None,
    )
    # Simulate mood update by setting instance vars directly (bypassing streaming path)
    wm._current_mood = "frustrated"
    wm._current_emoji = "😟"
    # Force prompt regeneration
    prompt = wm.system_prompt
    assert "Current mood: frustrated" in prompt, prompt
    assert "😟" in prompt, prompt
    # Ensure frustrated behavior instruction present
    assert "hurt" in prompt.lower(), prompt
