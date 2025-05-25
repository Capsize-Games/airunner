"""
Unit tests for airunner.utils.llm.language.detect_language
Covers language detection, enum mapping, and fallback logic.
"""

import pytest
from unittest.mock import patch, MagicMock
from airunner.utils.llm import language


@patch("airunner.utils.llm.language.FormatterExtended")
@patch("airunner.utils.llm.language.LanguageDetectorBuilder")
@patch("airunner.utils.llm.language.Language")
def test_detect_language_known(mock_Language, mock_Builder, mock_Formatter):
    # Setup mocks
    mock_Formatter.strip_nonlinguistic.return_value = "hello"
    detector = MagicMock()
    mock_Builder.from_languages.return_value.build.return_value = detector
    lang_obj = MagicMock()
    lang_obj.iso_code_639_1.name = "EN"
    detector.detect_language_of.return_value = lang_obj
    # Should map to AvailableLanguage.EN
    result = language.detect_language("hello")
    assert result == language.AvailableLanguage.EN


@patch("airunner.utils.llm.language.FormatterExtended")
@patch("airunner.utils.llm.language.LanguageDetectorBuilder")
@patch("airunner.utils.llm.language.Language")
def test_detect_language_none(mock_Language, mock_Builder, mock_Formatter):
    mock_Formatter.strip_nonlinguistic.return_value = ""
    detector = MagicMock()
    mock_Builder.from_languages.return_value.build.return_value = detector
    detector.detect_language_of.return_value = None
    result = language.detect_language("")
    assert result == language.AvailableLanguage.EN  # fallback


@patch("airunner.utils.llm.language.FormatterExtended")
@patch("airunner.utils.llm.language.LanguageDetectorBuilder")
@patch("airunner.utils.llm.language.Language")
def test_detect_language_japanese_korean(
    mock_Language, mock_Builder, mock_Formatter
):
    mock_Formatter.strip_nonlinguistic.return_value = "こんにちは"
    detector = MagicMock()
    mock_Builder.from_languages.return_value.build.return_value = detector
    lang_obj = MagicMock()
    # Test Japanese
    lang_obj.iso_code_639_1.name = "JA"
    detector.detect_language_of.return_value = lang_obj
    result = language.detect_language("こんにちは")
    assert result == language.AvailableLanguage.JP
    # Test Korean
    lang_obj.iso_code_639_1.name = "KO"
    result = language.detect_language("안녕하세요")
    assert result == language.AvailableLanguage.KR


@patch("airunner.utils.llm.language.FormatterExtended")
@patch("airunner.utils.llm.language.LanguageDetectorBuilder")
@patch("airunner.utils.llm.language.Language")
def test_detect_language_enum_fallback(
    mock_Language, mock_Builder, mock_Formatter
):
    mock_Formatter.strip_nonlinguistic.return_value = "foo"
    detector = MagicMock()
    mock_Builder.from_languages.return_value.build.return_value = detector
    lang_obj = MagicMock()
    lang_obj.iso_code_639_1.name = "ZZ"  # Not in AvailableLanguage
    detector.detect_language_of.return_value = lang_obj
    result = language.detect_language("foo")
    assert result == language.AvailableLanguage.EN  # fallback
