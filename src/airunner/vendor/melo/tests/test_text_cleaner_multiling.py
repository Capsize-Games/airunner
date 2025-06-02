"""
Tests for melo.text.cleaner_multiling
Covers all public functions, edge cases, and error handling.
"""

import pytest
import re
from melo.text import cleaner_multiling


@pytest.mark.parametrize(
    "text,expected",
    [
        ("你好，世界。", "你好,世界."),
        ("Hello！How are you？", "Hello!How are you?"),
        ("...", "."),
        ("“quote”‘single’", "'quote''single'"),
        ("（test）", "'test'"),
        ("【test】", "'test'"),
        ("—", ""),
        ("～ ~", "- -"),
        ("「text」", "'text'"),
    ],
)
def test_replace_punctuation(text, expected):
    assert cleaner_multiling.replace_punctuation(text) == expected


@pytest.mark.parametrize(
    "text,expected",
    [
        ("ABCdef", "abcdef"),
        ("123!", "123!"),
    ],
)
def test_lowercase(text, expected):
    assert cleaner_multiling.lowercase(text) == expected


@pytest.mark.parametrize(
    "text,expected",
    [
        ("a   b\tc\nd", "a b c d"),
        ("   leading and trailing   ", "leading and trailing"),
        ("single", "single"),
    ],
)
def test_collapse_whitespace(text, expected):
    assert cleaner_multiling.collapse_whitespace(text) == expected


@pytest.mark.parametrize(
    "text,expected",
    [
        (",,Hello", "Hello"),
        ("...!Hi", "Hi"),
        ("?Test", "Test"),
        ("NoPunct", "NoPunct"),
    ],
)
def test_remove_punctuation_at_begin(text, expected):
    assert cleaner_multiling.remove_punctuation_at_begin(text) == expected


@pytest.mark.parametrize(
    "text,expected",
    [
        ("<test>", "test"),
        ("[abc]", "abc"),
        ("'quoted'", "quoted"),
        ("no symbols", "no symbols"),
        ("«abc»", "abc"),
        ('"abc"', "abc"),
    ],
)
def test_remove_aux_symbols(text, expected):
    assert cleaner_multiling.remove_aux_symbols(text) == expected


@pytest.mark.parametrize(
    "text,lang,expected",
    [
        ("a-b", "en", "a b"),
        ("a-b", "ca", "ab"),
        ("a:b", "en", "a,b"),
        ("a;b", "en", "a,b"),
        ("a&b", "en", "a and b"),
        ("a&b", "fr", "a et b"),
        ("a&b", "pt", "a e b"),
        ("a&b", "ca", "a i b"),
        ("a'b", "ca", "ab"),
        ("a'b", "es", "ab"),
        ("a&b", "es", "ayb"),
    ],
)
def test_replace_symbols(text, lang, expected):
    assert cleaner_multiling.replace_symbols(text, lang) == expected


@pytest.mark.parametrize(
    "text,cased,lang,expected",
    [
        ("Hello, WORLD!", False, "en", "hello, world!"),
        ("Bonjour & bienvenue!", False, "fr", "bonjour et bienvenue!"),
        ("Olá & bem-vindo!", False, "pt", "olá e bem vindo!"),
        ("Hola & bienvenido!", False, "es", "hola y bienvenido!"),
        ("si l'avi cau, diguem-ho", False, "ca", "si lavi cau, diguemho."),
        ("   ...", False, "en", "."),
        ("", False, "en", ""),
        ("Test", True, "en", "Test."),
    ],
)
def test_unicleaners(text, cased, lang, expected):
    assert cleaner_multiling.unicleaners(text, cased, lang) == expected


# Edge: already ends with punctuation
@pytest.mark.parametrize(
    "text,expected_end",
    [
        ("test.", "."),
        ("test!", "!"),
        ("test?", "?"),
        ("test-", "."),  # After cleaning, hyphen is removed, period is added
        ("test…", "."),  # After cleaning, ellipsis is replaced with period
    ],
)
def test_unicleaners_ends_with_punct(text, expected_end):
    result = cleaner_multiling.unicleaners(text, False, "en")
    assert result.endswith(expected_end)
    assert result.count(".") <= 1  # Only one period at end if not already present


# Edge: whitespace collapse and punctuation
@pytest.mark.parametrize(
    "text,expected",
    [
        ("   a   b   c   ", "a b c."),
        ("a\tb\nc", "a b.c."),
    ],
)
def test_unicleaners_whitespace(text, expected):
    assert cleaner_multiling.unicleaners(text, False, "en") == expected
