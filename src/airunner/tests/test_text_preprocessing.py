"""
Unit tests for airunner.utils.llm.text_preprocessing
"""

import pytest


def test_prepare_text_for_tts(monkeypatch):
    monkeypatch.setattr(
        "airunner.utils.llm.text_preprocessing.replace_unspeakable_characters",
        lambda t: t + "_u",
    )
    monkeypatch.setattr(
        "airunner.utils.llm.text_preprocessing.strip_emoji_characters",
        lambda t: t + "_e",
    )
    monkeypatch.setattr(
        "airunner.utils.llm.text_preprocessing.replace_numbers_with_words",
        lambda t: t + "_n",
    )
    monkeypatch.setattr(
        "airunner.utils.llm.text_preprocessing.replace_misc_with_words",
        lambda t: t + "_m",
    )
    from airunner.utils import prepare_text_for_tts

    assert prepare_text_for_tts("x") == "x_u_e_n_m"


def test_replace_unspeakable_characters():
    from airunner.utils import replace_unspeakable_characters

    assert "..." not in replace_unspeakable_characters("foo...bar")
    assert "“”" not in replace_unspeakable_characters("“foo”")


def test_strip_emoji_characters():
    from airunner.utils import strip_emoji_characters

    assert strip_emoji_characters("hello😀") == "hello"


def test_replace_numbers_with_words():
    from airunner.utils import replace_numbers_with_words

    out = replace_numbers_with_words("I have 2 apples")
    assert "two" in out


def test_replace_misc_with_words():
    from airunner.utils import replace_misc_with_words

    assert "degrees Fahrenheit" in replace_misc_with_words("100°F")
    assert "degrees Celsius" in replace_misc_with_words("100°C")
    assert "degrees" in replace_misc_with_words("100°")


def test_roman_to_int():
    from airunner.utils import roman_to_int

    assert "4" in roman_to_int("IV")
    assert "2024" in roman_to_int("MMXXIV")
