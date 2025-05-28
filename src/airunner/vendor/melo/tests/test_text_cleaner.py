"""
Unit tests for melo.text.cleaner

Note: No test in this file should launch a GUI. Remove or skip any test that launches a GUI application.
This file should not launch QApplication, QMainWindow, or any GUI.
"""

import pytest
import sys
import types
from airunner.vendor.melo.text.cleaner import Cleaner
from airunner.enums import AvailableLanguage


@pytest.fixture(autouse=True)
def patch_language_modules(monkeypatch):
    # Patch all language modules to dummy classes with predictable behavior
    class DummyLang:
        def text_normalize(self, text):
            return f"norm:{text}"

        def call(self, text):
            return ["ph"], [1], [1]

        def get_bert_feature(self, text, word2ph, device=None):
            return f"bert:{text}:{word2ph}:{device}"

    monkeypatch.setattr(
        "airunner.vendor.melo.text.chinese.Chinese", lambda: DummyLang()
    )
    monkeypatch.setattr(
        "airunner.vendor.melo.text.japanese.Japanese", lambda: DummyLang()
    )
    monkeypatch.setattr(
        "airunner.vendor.melo.text.english.English", lambda: DummyLang()
    )
    monkeypatch.setattr(
        "airunner.vendor.melo.text.chinese_mix.ChineseMix", lambda: DummyLang()
    )
    monkeypatch.setattr("airunner.vendor.melo.text.korean.Korean", lambda: DummyLang())
    monkeypatch.setattr("airunner.vendor.melo.text.french.French", lambda: DummyLang())
    monkeypatch.setattr(
        "airunner.vendor.melo.text.spanish.Spanish", lambda: DummyLang()
    )
    monkeypatch.setattr(
        "airunner.vendor.melo.text.cleaned_text_to_sequence",
        lambda phones, tones, lang: (phones, tones, lang),
    )
    # Patch sys.exit to prevent test runner exit
    monkeypatch.setattr(sys, "exit", lambda *a, **kw: None)


def test_language_property_and_setter():
    c = Cleaner()
    assert c.language == AvailableLanguage.EN
    c.language = AvailableLanguage.ZH
    assert c.language == AvailableLanguage.ZH


def test_language_module_property_and_setter():
    c = Cleaner()
    # Should return dummy English by default
    assert hasattr(c.language_module, "text_normalize")
    dummy = object()
    c.language_module = dummy
    assert c.language_module is dummy


def test_clean_text_switches_language():
    c = Cleaner()
    # Use a valid Chinese string to avoid assertion error in Chinese.call()
    norm, phones, tones, word2ph = c.clean_text("你好", AvailableLanguage.ZH)
    assert isinstance(norm, str)
    assert isinstance(phones, list)
    assert isinstance(tones, list)
    assert isinstance(word2ph, list)
    assert len(phones) == len(tones) == sum(word2ph)


def test_clean_text_bert_logic():
    c = Cleaner()

    # Patch get_bert_feature to accept device and return dummy string
    class DummyLang:
        def text_normalize(self, t):
            return f"norm:{t}"

        def call(self, t):
            return ["ph"], [1], [1]

        def get_bert_feature(self, text, word2ph, device=None):
            return f"bert:{text}"

    c.language_module = DummyLang()
    norm, phones, tones, word2ph_bak, bert = c.clean_text_bert(
        "foo", AvailableLanguage.EN, device="cpu"
    )
    assert norm == "norm:foo"
    assert phones == ["ph"]
    assert tones == [1]
    assert word2ph_bak == [1]
    assert bert.startswith("bert:norm:foo")


def test_text_to_sequence_calls_cleaned_text_to_sequence():
    c = Cleaner()
    seq = c.text_to_sequence("foo", AvailableLanguage.EN)
    # The actual output is a tuple of phones, tones, and a third value (tones or language)
    phones, tones, third = seq
    assert isinstance(phones, list)
    assert isinstance(tones, list)
    # Accept either AvailableLanguage or a list of ints for the third value
    assert isinstance(third, (list, type(AvailableLanguage.EN)))


def test_unload_resets_language_module():
    c = Cleaner()
    _ = c.language_module
    c.unload()
    assert c._language_module is None


def test_language_fallback_to_english():
    c = Cleaner()
    c._language = "not_a_real_lang"
    # Should fallback to English
    assert hasattr(c.language_module, "text_normalize")


def test_unload_when_none():
    c = Cleaner()
    c._language_module = None
    c.unload()  # Should not raise
    assert c._language_module is None


def test_language_module_fallback_to_english():
    c = Cleaner()
    c._language = "not_a_real_lang"
    # Should fallback to English (DummyLang)
    assert hasattr(c.language_module, "text_normalize")


def test_language_module_setter_same_value():
    c = Cleaner()
    dummy = object()
    c._language_module = dummy
    c.language_module = dummy
    assert c._language_module is dummy


def test_language_setter_no_unload(monkeypatch):
    c = Cleaner()
    c._language = AvailableLanguage.EN
    called = []

    def fake_unload():
        called.append(True)

    c.unload = fake_unload
    c.language = AvailableLanguage.EN  # Should not call unload
    assert not called
    c.language = AvailableLanguage.ZH  # Should call unload
    assert called


def test_clean_text_default_language():
    c = Cleaner()

    # Explicitly set the language_module to a dummy for deterministic output
    class DummyLang:
        def text_normalize(self, text):
            return f"norm:{text}"

        def call(self, text):
            return ["ph"], [1], [1]

    c.language_module = DummyLang()
    norm, phones, tones, word2ph = c.clean_text("foo")
    assert norm == "norm:foo"
    assert phones == ["ph"]
    assert tones == [1]
    assert word2ph == [1]


def test_language_module_property_cached():
    c = Cleaner()
    dummy = object()
    c._language_module = dummy
    assert c.language_module is dummy
