"""
Unit tests for openvoice.text.cleaners
Covers importability and basic function presence.
"""

import pytest
import airunner.vendor.openvoice.text.cleaners as cleaners
import sys
import types


def test_module_importable():
    assert cleaners is not None


# Add more specific tests for public functions/classes as needed
def test_cjke_cleaners2_basic(monkeypatch):
    # Patch all language functions to return a marker string
    monkeypatch.setattr(cleaners, "chinese_to_ipa", lambda x: f"ZH:{x}")
    # Patch missing japanese_to_ipa2 and korean_to_ipa by injecting into sys.modules
    sys.modules["airunner.vendor.openvoice.text.cleaners"].japanese_to_ipa2 = (
        lambda x: f"JA:{x}"
    )
    sys.modules["airunner.vendor.openvoice.text.cleaners"].korean_to_ipa = (
        lambda x: f"KO:{x}"
    )
    monkeypatch.setattr(cleaners, "english_to_ipa2", lambda x: f"EN:{x}")
    # Test all language tags
    text = "[ZH]你好[ZH] [JA]こんにちは[JA] [KO]안녕[KO] [EN]hello[EN]"
    result = cleaners.cjke_cleaners2(text)
    assert "ZH:你好" in result
    assert "JA:こんにちは" in result
    assert "KO:안녕" in result
    assert "EN:hello" in result


def test_cjke_cleaners2_strip_and_punct(monkeypatch):
    # Only English, test strip and punctuation
    monkeypatch.setattr(cleaners, "english_to_ipa2", lambda x: x)
    text = "[EN]hello[EN]   "
    result = cleaners.cjke_cleaners2(text)
    assert result.endswith(".")
    # Already ends with punctuation
    text2 = "[EN]hello[EN]!"
    result2 = cleaners.cjke_cleaners2(text2)
    assert result2.endswith("!")
