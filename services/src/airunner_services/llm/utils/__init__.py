"""Utility exports for service-owned LLM helpers."""

from airunner_services.llm.utils.parse_template import parse_template
from airunner_services.llm.utils.strip_names_from_message import (
    strip_names_from_message,
)
from airunner_services.llm.utils.text_preprocessing import (
    prepare_text_for_tts,
    replace_unspeakable_characters,
    strip_emoji_characters,
    replace_numbers_with_words,
    replace_misc_with_words,
)


__all__ = [
    "parse_template",
    "strip_names_from_message",
    "prepare_text_for_tts",
    "replace_unspeakable_characters",
    "strip_emoji_characters",
    "replace_numbers_with_words",
    "replace_misc_with_words",
    "get_chatbot",
]


def __getattr__(name: str):
    """Resolve cycle-prone utility exports lazily."""
    if name == "get_chatbot":
        from airunner_services.llm.utils.get_chatbot import get_chatbot

        return get_chatbot
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
