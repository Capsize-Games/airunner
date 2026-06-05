"""Utility exports for service-owned LLM helpers."""

from airunner_services.llm.utils.parse_template import parse_template
from airunner_services.llm.utils.strip_names_from_message import (
    strip_names_from_message,
)
from airunner_services.utils.text.tts_preprocessing import (
    prepare_text_for_tts,
    replace_misc_with_words,
    replace_numbers_with_words,
    replace_unspeakable_characters,
    strip_emoji_characters,
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
    "append_stream_text",
    "combine_stream_chunks",
    "detect_language",
    "extract_thinking_and_response",
    "GPTOSSParseResult",
    "GPTOSSStreamParser",
    "needs_stream_space",
    "parse_gpt_oss_response",
    "parse_thinking_from_tokens",
    "parse_thinking_response",
    "prepare_stream_chunk",
    "strip_nonlinguistic_text",
    "strip_thinking_tags",
]


def __getattr__(name: str):
    """Resolve cycle-prone utility exports lazily."""
    if name == "get_chatbot":
        from airunner_services.llm.get_chatbot import get_chatbot

        return get_chatbot
    if name in {
        "append_stream_text",
        "combine_stream_chunks",
        "needs_stream_space",
        "prepare_stream_chunk",
    }:
        from airunner_services.llm import stream_text

        return getattr(stream_text, name)
    if name in {
        "extract_thinking_and_response",
        "parse_thinking_from_tokens",
        "parse_thinking_response",
        "strip_thinking_tags",
    }:
        from airunner_services.llm import thinking_parser

        return getattr(thinking_parser, name)
    if name in {
        "GPTOSSParseResult",
        "GPTOSSStreamParser",
        "parse_gpt_oss_response",
    }:
        from airunner_services.llm import gpt_oss_parser

        return getattr(gpt_oss_parser, name)
    if name in {
        "detect_language",
        "strip_nonlinguistic_text",
    }:
        from airunner_services.utils.text import language_detection

        return getattr(language_detection, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
