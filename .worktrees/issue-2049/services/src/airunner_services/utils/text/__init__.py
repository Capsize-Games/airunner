"""Service-owned text helpers."""

from airunner_services.utils.text.formatter import Formatter
from airunner_services.utils.text.formatter_extended import (
	FormatterExtended,
)
from airunner_services.utils.text.tts_preprocessing import (
	prepare_text_for_tts,
)
from airunner_services.utils.text.tts_preprocessing import (
	replace_misc_with_words,
)
from airunner_services.utils.text.tts_preprocessing import (
	replace_numbers_with_words,
)
from airunner_services.utils.text.tts_preprocessing import (
	replace_unspeakable_characters,
)
from airunner_services.utils.text.tts_preprocessing import roman_to_int
from airunner_services.utils.text.tts_preprocessing import (
	strip_emoji_characters,
)


__all__ = [
	"detect_language",
	"Formatter",
	"FormatterExtended",
	"prepare_text_for_tts",
	"replace_misc_with_words",
	"replace_numbers_with_words",
	"replace_unspeakable_characters",
	"roman_to_int",
	"strip_emoji_characters",
]


def __getattr__(name: str):
	"""Resolve optional text exports lazily.

	``language_detection`` imports the optional ``lingua`` package at module
	import time. Importing the text-helpers package (which the download
	workers pull in) must not require lingua, so the language-detection
	helpers resolve only when actually used (issue #2054).
	"""
	if name in {"detect_language", "strip_nonlinguistic_text"}:
		from airunner_services.utils.text import language_detection

		return getattr(language_detection, name)
	raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
