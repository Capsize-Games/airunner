"""
Unit tests for melo.text.english

Covers: text_normalize, call, refine_syllables, refine_ph, post_replace_ph, and edge cases.
"""

import pytest
from unittest import mock
from airunner.vendor.melo.text.english import English


def test_text_normalize_abbreviation(monkeypatch):
    e = English()
    # Patch at the import location used by English
    monkeypatch.setattr(
        "airunner.vendor.melo.text.english.expand_abbreviations",
        lambda t, lang="en": t + "_abbr",
    )
    monkeypatch.setattr(
        "airunner.vendor.melo.text.english.expand_time_english", lambda t: t + "_time"
    )
    monkeypatch.setattr(
        "airunner.vendor.melo.text.english.normalize_numbers", lambda t: t + "_num"
    )
    out = e.text_normalize("foo")
    assert out.endswith("_abbr") and "_num" in out and "_time" in out


def test_call_dict_hit(monkeypatch):
    e = English()
    e.eng_dict = {"FOO": [["F", "UW1"]]}
    e._g2p = lambda w: ["F", "UW1"]
    phones, tones, word2ph = e.call("foo", pad_start_end=False)
    assert phones == ["f", "uw"]
    assert all(isinstance(t, int) for t in tones)
    assert word2ph == [1, 1]


def test_call_oov(monkeypatch):
    e = English()
    e.eng_dict = {}
    e._g2p = lambda w: ["F", "UW1"]
    phones, tones, word2ph = e.call("foo", pad_start_end=False)
    assert phones == ["f", "uw"]
    assert all(isinstance(t, int) for t in tones)
    assert word2ph == [1, 1]


def test_call_single_char_not_in_dict():
    e = English()
    e.eng_dict = {}
    phones, tones, word2ph = e.call("x", pad_start_end=False)
    assert phones == ["x"]
    assert tones == [0]
    assert word2ph == [1]


def test_call_tokenized():
    e = English()
    e.eng_dict = {"FOO": [["F", "UW1"]], "TEST": [["T", "EH1", "S", "T"]]}
    phones, tones, word2ph = e.call(
        "test foo", pad_start_end=False, tokenized=["test", "foo"]
    )
    assert phones == ["t", "eh", "s", "t", "f", "uw"]
    assert len(tones) == 6
    assert word2ph == [4, 2]


def test_call_pad_start_end():
    e = English()
    e.eng_dict = {"FOO": [["F", "UW1"]]}
    phones, tones, word2ph = e.call("foo", pad_start_end=True)
    assert phones[0] == phones[-1] == "_"
    assert tones[0] == tones[-1] == 0
    assert word2ph[0] == word2ph[-1] == 1


def test_refine_syllables_and_ph():
    e = English()
    phs, tones = e.refine_syllables([["EH1", "T"], ["S"]])
    assert phs == ["eh", "t", "s"]
    assert tones == [2, 0, 0]
    ph, tone = e.refine_ph("EH1")
    assert ph == "eh" and tone == 2
    ph, tone = e.refine_ph("T")
    assert ph in ("t", "UNK") and tone == 0


def test_post_replace_ph():
    e = English()
    # The default mapping returns 'UNK' for unknown phones
    assert e.post_replace_ph("AA1") == "UNK"
    assert e.post_replace_ph("T") in ("t", "UNK")


def test_call_empty(monkeypatch):
    e = English()
    e.eng_dict = {}

    # Patch tokenizer to avoid model loading
    class DummyTokenizer:
        def tokenize(self, text):
            return []

    e._tokenizer = DummyTokenizer()
    phones, tones, word2ph = e.call("", pad_start_end=False)
    assert phones == []
    assert tones == []
    assert word2ph == []
