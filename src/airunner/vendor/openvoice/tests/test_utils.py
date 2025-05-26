"""
Unit tests for openvoice.utils
"""

import pytest
import importlib
import os
import tempfile
import numpy as np
from airunner.enums import AvailableLanguage

utils = importlib.import_module("airunner.vendor.openvoice.utils")


def test_utils_module_importable():
    assert utils is not None


def test_get_hparams_from_file(tmp_path):
    config = '{"foo": 1, "bar": {"baz": 2}}'
    config_path = tmp_path / "config.json"
    config_path.write_text(config, encoding="utf-8")
    hparams = utils.get_hparams_from_file(str(config_path))
    assert hparams.foo == 1
    assert hparams.bar.baz == 2


def test_hparams_class():
    h = utils.HParams(a=1, b=2)
    assert h["a"] == 1
    h["c"] = 3
    assert h.c == 3
    assert "a" in h
    assert len(h) == 3
    assert isinstance(repr(h), str)
    assert set(h.keys()) == {"a", "b", "c"}
    assert set(h.items()) == {("a", 1), ("b", 2), ("c", 3)}
    assert set(h.values()) == {1, 2, 3}


def test_string_to_bits_and_bits_to_string():
    s = "abc"
    bits = utils.string_to_bits(s, pad_len=3)
    assert bits.shape == (3, 8)
    s2 = utils.bits_to_string(bits)
    assert s2[:3] == s


def test_split_sentence_latin():
    text = "This is a sentence. This is another one! Short? Yes."
    out = utils.split_sentence(text, min_len=2, language=AvailableLanguage.EN)
    assert isinstance(out, list)
    assert any("This is a sentence." in s for s in out)


def test_split_sentence_zh():
    text = "这是一个句子。这是另一个！短？是。"
    out = utils.split_sentence(text, min_len=2, language=AvailableLanguage.ZH)
    assert isinstance(out, list)
    assert any("这是一个句子." in s for s in out)


def test_merge_short_sentences_latin():
    sens = ["Hi.", "A", "This is long enough."]
    merged = utils.merge_short_sentences_latin(sens)
    assert isinstance(merged, list)
    assert any("Hi. A" in s for s in merged)


def test_merge_short_sentences_zh():
    sens = ["嗨。", "是", "这很长。"]
    merged = utils.merge_short_sentences_zh(sens)
    assert isinstance(merged, list)
    assert any("嗨。 是" in s for s in merged)


def test_merge_short_sentences_latin_triggers_except():
    # Only one short sentence, triggers IndexError in try block
    sens = ["A"]
    merged = utils.merge_short_sentences_latin(sens)
    assert merged == ["A"]


def test_merge_short_sentences_zh_triggers_except():
    # Only one short sentence, triggers IndexError in try block
    sens = ["是"]
    merged = utils.merge_short_sentences_zh(sens)
    assert merged == ["是"]


def test_merge_short_sentences_zh_pop_last():
    # Exactly two short sentences, triggers sens_out.pop(-1)
    sens = ["是", "也"]
    merged = utils.merge_short_sentences_zh(sens)
    # The two short sentences should be merged into one
    assert merged == ["是 也"]
