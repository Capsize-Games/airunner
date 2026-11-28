"""Unit tests for the auto-mood extraction helpers.

_classify_mood and _publish_mood_update were extracted to keep
_auto_update_mood within the long-function threshold. These tests
pin the keyword priority order and the publish side effects.
"""

from types import SimpleNamespace
from unittest.mock import MagicMock

from airunner_services.llm.managers.mixins.streaming_mixin import (
    StreamingMixin,
)


def _make_obj():
    obj = StreamingMixin.__new__(StreamingMixin)
    obj.logger = MagicMock()
    return obj


def test_classify_hostile_wins_over_positive():
    mood, emoji, _ = StreamingMixin._classify_mood("thanks, you stupid")
    assert mood == "frustrated"
    assert emoji == "😟"


def test_classify_positive():
    mood, emoji, message = StreamingMixin._classify_mood("thank you, helpful")
    assert mood == "happy"
    assert emoji == "😊"
    assert "appreciated" in message


def test_classify_confused():
    mood, emoji, _ = StreamingMixin._classify_mood("huh, unclear here")
    assert mood == "confused"
    assert emoji == "🤔"


def test_classify_neutral_default():
    mood, emoji, message = StreamingMixin._classify_mood("the sky is blue")
    assert mood == "neutral"
    assert emoji == "😐"
    assert "calm" in message


def test_publish_stores_and_updates_prompt(monkeypatch):
    obj = _make_obj()
    obj.system_prompt = "sys"
    obj.update_system_prompt = MagicMock()
    sink = MagicMock()

    import airunner_services.llm_workflow_events as events_mod

    monkeypatch.setattr(
        events_mod, "resolve_llm_workflow_event_sink", lambda owner: sink
    )
    obj._publish_mood_update("happy", "😊", "*happy*")
    assert obj._current_mood == "happy"
    assert obj._current_emoji == "😊"
    obj.update_system_prompt.assert_called_once_with("sys")
    sink.emit_bot_mood.assert_called_once_with(
        {"mood": "happy", "emoji": "😊"}
    )


def test_publish_warns_without_prompt_update():
    obj = _make_obj()
    obj._publish_mood_update("neutral", "😐", "*calm*")
    obj.logger.warning.assert_called_once()
