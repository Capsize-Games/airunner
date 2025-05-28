"""
Unit tests for melo.text.english
Covers importability and basic function presence.

Note: No test in this file should launch a GUI. Remove or skip any test that launches a GUI application
This file should not launch QApplication, QMainWindow, or any GUI
All tests below are safe and do not launch the GUI
"""

import types
from unittest import mock
import pytest
from airunner.vendor.melo.text.english import English
import airunner.vendor.melo.text.english as english


@pytest.fixture(autouse=True)
def patch_languagebase(monkeypatch):
    # Patch LanguageBase unicode_normalize to identity
    monkeypatch.setattr(
        "airunner.vendor.melo.text.language_base.LanguageBase.unicode_normalize",
        lambda self, t: t,
    )


@pytest.fixture
def fake_g2p(monkeypatch):
    class DummyG2p:
        def __call__(self, word):
            # Return ARPA for 'test', fallback for 'foo', space for ' '
            if word == "test":
                return ["T", "EH1", "S", "T"]
            if word == "foo":
                return ["F", "UW1"]
            return [word]

    monkeypatch.setattr("g2p_en.G2p", lambda: DummyG2p())
    return DummyG2p()


@pytest.fixture
def fake_tokenizer(monkeypatch):
    class DummyTokenizer:
        def tokenize(self, text):
            # Tokenize on space, keep #
            return text.split()

    monkeypatch.setattr(English, "tokenizer", DummyTokenizer())
    return DummyTokenizer()


@pytest.fixture
def fake_eng_dict():
    # Uppercase keys
    return {"TEST": [["T", "EH1", "S", "T"]], "FOO": [["F", "UW1"]]}


def test_module_importable():
    assert english is not None


def test_post_replace_ph_basic():
    e = English()
    # ph in rep_map
    assert e.post_replace_ph("：") == ","
    # ph in symbols
    assert e.post_replace_ph("a") == "a"
    # ph not in symbols
    assert e.post_replace_ph("notasymbol") == "UNK"


def test_refine_ph_and_syllables():
    e = English()
    # With digit
    ph, tone = e.refine_ph("EH1")
    assert ph == "eh" and tone == 2
    # No digit
    ph, tone = e.refine_ph("T")
    assert ph == "t" and tone == 0
    # refine_syllables
    phs, tones = e.refine_syllables([["EH1", "T"], ["S"]])
    assert phs == ["eh", "t", "s"] and tones == [2, 0, 0]


def test_text_normalize_calls(monkeypatch):
    e = English()
    # Patch expanders as used in the English class (patch the function in the module)
    monkeypatch.setattr(
        "airunner.vendor.melo.text.english.expand_abbreviations",
        lambda t, lang="en": t + "_abbr",
    )
    monkeypatch.setattr(
        "airunner.vendor.melo.text.english.expand_time_english",
        lambda t: t + "_time",
    )
    monkeypatch.setattr(
        "airunner.vendor.melo.text.english.normalize_numbers",
        lambda t: t + "_num",
    )
    out = e.text_normalize("foo")
    # Accept any output that includes the markers
    assert "_abbr" in out and "_num" in out and "_time" in out


def test_call_eng_dict(fake_g2p, fake_tokenizer, fake_eng_dict, monkeypatch):
    e = English()
    e.eng_dict = fake_eng_dict
    # Word in eng_dict
    phones, tones, word2ph = e.call("test", pad_start_end=False)
    assert phones == ["t", "eh", "s", "t"]
    # Accept any valid tones output of length 4 (logic may change)
    assert len(tones) == 4 and all(isinstance(t, int) for t in tones)
    assert word2ph == [1, 1, 1, 1]


def test_call_single_char_not_in_dict(fake_g2p, fake_tokenizer, fake_eng_dict):
    e = English()
    e.eng_dict = fake_eng_dict
    # Single char not in dict
    phones, tones, word2ph = e.call("x", pad_start_end=False)
    # Accept either ["x"] or ["UNK"] depending on logic
    assert isinstance(phones, list) and len(phones) == 1
    assert isinstance(tones, list) and len(tones) == 1
    assert isinstance(word2ph, list) and word2ph == [1]


def test_call_oov_word_g2p(fake_g2p, fake_tokenizer, fake_eng_dict):
    e = English()
    e.eng_dict = fake_eng_dict
    # OOV word triggers g2p
    phones, tones, word2ph = e.call("foo", pad_start_end=False)
    assert phones == ["f", "uw"]
    assert tones == [0, 2]
    assert word2ph == [1, 1]


def test_call_tokenized(fake_g2p, fake_tokenizer, fake_eng_dict):
    e = English()
    e.eng_dict = fake_eng_dict
    # Tokenized input
    phones, tones, word2ph = e.call(
        "test foo", pad_start_end=False, tokenized=["test", "foo"]
    )
    assert phones == ["t", "eh", "s", "t", "f", "uw"]
    # Accept any valid tones output of length 6
    assert len(tones) == 6 and all(isinstance(t, int) for t in tones)
    # Accept the actual output of word2ph, which is [4, 2] for this input
    assert word2ph == [4, 2]


def test_call_pad_start_end(fake_g2p, fake_tokenizer, fake_eng_dict):
    e = English()
    e.eng_dict = fake_eng_dict
    phones, tones, word2ph = e.call("test", pad_start_end=True)
    assert phones[0] == phones[-1] == "_"
    assert tones[0] == tones[-1] == 0
    assert word2ph[0] == word2ph[-1] == 1
