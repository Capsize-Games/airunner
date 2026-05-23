"""Service-owned helpers for language detection."""

from __future__ import annotations

import re

from lingua import Language
from lingua import LanguageDetectorBuilder

from airunner_services.contract_enums import AvailableLanguage


_DETECTOR = LanguageDetectorBuilder.from_languages(
    Language.ENGLISH,
    Language.FRENCH,
    Language.SPANISH,
    Language.KOREAN,
    Language.CHINESE,
    Language.JAPANESE,
).build()


def strip_nonlinguistic_text(text: str) -> str:
    """Remove code and LaTeX fragments before language detection."""
    text = re.sub(r"\$\$.*?\$\$", " ", text, flags=re.DOTALL)
    text = re.sub(r"\$[^$]+\$", " ", text)
    text = re.sub(r"\\\[.*?\\\]", " ", text, flags=re.DOTALL)
    text = re.sub(r"\\\(.*?\\\)", " ", text, flags=re.DOTALL)
    text = re.sub(r"```[\w\W]*?```", " ", text)
    text = re.sub(r"`[^`]+`", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _to_available_language(language: Language | None) -> AvailableLanguage:
    """Map a Lingua language result to the shared language enum."""
    if language is None:
        return AvailableLanguage.EN
    name = language.iso_code_639_1.name
    if name == "JA":
        return AvailableLanguage.JP
    if name == "KO":
        return AvailableLanguage.KR
    try:
        return AvailableLanguage(name)
    except ValueError:
        return AvailableLanguage.EN


def detect_language(text: str) -> AvailableLanguage:
    """Detect the best matching language for user-provided text."""
    clean_text = strip_nonlinguistic_text(text)
    if not clean_text:
        return AvailableLanguage.EN
    language = _DETECTOR.detect_language_of(clean_text)
    return _to_available_language(language)


__all__ = ["detect_language", "strip_nonlinguistic_text"]
