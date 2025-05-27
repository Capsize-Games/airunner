"""
Unit tests for openvoice.text.english
Covers importability and basic function presence.
"""

import pytest
import airunner.vendor.openvoice.text.english as english


def test_module_importable():
    assert english is not None


def test_expand_abbreviations():
    assert (
        english.expand_abbreviations("Dr. Smith met Mr. Jones.")
        == "doctor Smith met mister Jones."
    )


def test_collapse_whitespace():
    assert english.collapse_whitespace("a   b\n\tc") == "a b c"


def test_normalize_numbers():
    # Test comma numbers, pounds, dollars, decimals, ordinals, and plain numbers
    s = "1,234 £5 $6.50 3.14 21st 42"
    out = english.normalize_numbers(s)
    assert "one thousand two hundred thirty-four" in out
    assert "5 pounds" in out
    assert "6 dollars, 50 cents" in out
    assert "3 point 14" in out
    assert "twenty-first" in out
    assert "forty-two" in out


def test_mark_dark_l():
    # Should mark 'l' not followed by a vowel
    assert english.mark_dark_l("ball fall l ") == "baɫl faɫl ɫ "


def test_english_to_ipa():
    # Should return IPA string
    out = english.english_to_ipa("Hello, world!")
    assert isinstance(out, str)
    assert len(out) > 0


def test_english_to_lazy_ipa():
    out = english.english_to_lazy_ipa("Hello, world!")
    assert isinstance(out, str)
    assert len(out) > 0


def test_english_to_ipa2():
    out = english.english_to_ipa2("Hello, world!")
    assert isinstance(out, str)
    assert len(out) > 0


def test_english_to_lazy_ipa2():
    out = english.english_to_lazy_ipa2("Hello, world!")
    assert isinstance(out, str)
    assert len(out) > 0


def test__remove_commas():
    m = type("M", (), {"group": lambda self, i: "1,234"})()
    assert english._remove_commas(m) == "1234"


def test__expand_decimal_point():
    m = type("M", (), {"group": lambda self, i: "3.14"})()
    assert english._expand_decimal_point(m) == "3 point 14"


def test__expand_dollars():
    class M:
        def group(self, i):
            return "12.34"

    m = M()
    assert "dollars" in english._expand_dollars(m)
    m2 = type("M", (), {"group": lambda self, i: "0.99"})()
    assert "cent" in english._expand_dollars(m2)
    m3 = type("M", (), {"group": lambda self, i: "1.00"})()
    assert "dollar" in english._expand_dollars(m3)
    m4 = type("M", (), {"group": lambda self, i: "0.00"})()
    assert "zero dollars" in english._expand_dollars(m4)


def test__expand_ordinal():
    # Mock a match object where group(1) is the number part (e.g., "21")
    # and group(0) or group(2) could be the suffix or full string if needed by other tests.
    def mock_group(self, i):
        if i == 1:
            return "21"  # The number part for _expand_ordinal
        elif i == 0:
            return "21st"  # The full match
        elif i == 2:
            return "st"  # The suffix
        return None

    m = type("M", (), {"group": mock_group})()
    assert "twenty-first" in english._expand_ordinal(m)


def test__expand_number():
    m = type("M", (), {"group": lambda self, i: "2024"})()
    assert "two thousand" in english._expand_number(m)
    m2 = type("M", (), {"group": lambda self, i: "42"})()
    assert "forty-two" in english._expand_number(m2)
