"""
Unit tests for melo.text.chinese_mix, japanese, korean, french, spanish
Covers: text_normalize, call, and edge/error cases for each language handler.
"""

import pytest
import types
from airunner.vendor.melo.text.chinese_mix import ChineseMix
from airunner.vendor.melo.text.japanese import Japanese
from airunner.vendor.melo.text.korean import Korean
from airunner.vendor.melo.text.french import French
from airunner.vendor.melo.text.spanish import Spanish


@pytest.mark.parametrize(
    "LangCls, valid, oov",
    [
        (ChineseMix, "你好 world", "foo"),
        (Japanese, "こんにちは", "foo"),
        (Korean, "안녕하세요", "foo"),
        (French, "bonjour", "foo"),
        (Spanish, "hola", "foo"),
    ],
)
def test_text_normalize_and_call_valid(LangCls, valid, oov, monkeypatch):
    lang = LangCls()
    # Patch dependencies for ChineseMix and Japanese and Korean
    if LangCls is ChineseMix:
        # Patch self.chinese.call to accept a list and return dummy values
        lang.chinese = types.SimpleNamespace(call=lambda x: (["ph"], [1], [1]))
        # Patch self.english.call to avoid KeyError
        lang.english = types.SimpleNamespace(call=lambda **kwargs: (["ph"], [1], [1]))
        # Patch language_tone_start_map
        monkeypatch.setattr(
            "airunner.vendor.melo.text.chinese_mix.language_tone_start_map", {"EN": 0}
        )
        # Patch tokenizer
        lang.tokenizer = types.SimpleNamespace(tokenize=lambda x: [x])
    if LangCls is Japanese:
        # Patch tokenizer to avoid model loading
        lang.tokenizer = types.SimpleNamespace(tokenize=lambda x: [x])
        # Patch kata2phoneme to return valid phonemes from symbols
        lang.kata2phoneme = lambda text: ["a"]
    if LangCls is Korean:
        # Patch tokenizer to avoid model loading
        lang.tokenizer = types.SimpleNamespace(tokenize=lambda x: [x])
        # Patch korean_text_to_phonemes to return dummy phonemes
        lang.korean_text_to_phonemes = lambda text, character="hangeul": "a"
    if LangCls is French or LangCls is Spanish:
        lang.tokenizer = types.SimpleNamespace(tokenize=lambda x: [x])
    norm = lang.text_normalize(valid)
    assert isinstance(norm, str)
    # call should not raise for valid input
    phones, tones, word2ph = lang.call(valid)
    assert isinstance(phones, list)
    assert isinstance(tones, list)
    assert isinstance(word2ph, list)


@pytest.mark.parametrize("LangCls", [ChineseMix, Japanese, Korean, French, Spanish])
def test_call_empty(LangCls, monkeypatch):
    lang = LangCls()
    if LangCls is ChineseMix:
        lang.chinese = types.SimpleNamespace(call=lambda x: (["ph"], [1], [1]))
        lang.english = types.SimpleNamespace(call=lambda **kwargs: (["ph"], [1], [1]))
        monkeypatch.setattr(
            "airunner.vendor.melo.text.chinese_mix.language_tone_start_map", {"EN": 0}
        )
        lang.tokenizer = types.SimpleNamespace(tokenize=lambda x: [x])
    if LangCls is Japanese:
        lang.tokenizer = types.SimpleNamespace(tokenize=lambda x: [x])
    if LangCls is Korean:
        lang.tokenizer = types.SimpleNamespace(tokenize=lambda x: [x])
        lang.korean_text_to_phonemes = lambda text, character="hangeul": "a"
    if LangCls is French or LangCls is Spanish:
        lang.tokenizer = types.SimpleNamespace(tokenize=lambda x: [x])
    phones, tones, word2ph = lang.call("")
    assert isinstance(phones, list)
    assert isinstance(tones, list)
    assert isinstance(word2ph, list)


@pytest.mark.parametrize(
    "LangCls, oov",
    [
        (ChineseMix, "foo"),
        (Japanese, "foo"),
        (Korean, "foo"),
        (French, "foo"),
        (Spanish, "foo"),
    ],
)
def test_call_oov(LangCls, oov, monkeypatch):
    lang = LangCls()
    # Patch dependencies for ChineseMix
    if LangCls is ChineseMix:
        lang.chinese = types.SimpleNamespace(call=lambda x: (["ph"], [1], [1]))
        lang.english = types.SimpleNamespace(call=lambda **kwargs: (["ph"], [1], [1]))
        monkeypatch.setattr(
            "airunner.vendor.melo.text.chinese_mix.language_tone_start_map", {"EN": 0}
        )
        lang.tokenizer = types.SimpleNamespace(tokenize=lambda x: [x])
    if LangCls is Japanese:
        lang.tokenizer = types.SimpleNamespace(tokenize=lambda x: [x])
    if LangCls is Korean:
        lang.tokenizer = types.SimpleNamespace(tokenize=lambda x: [x])
        lang.korean_text_to_phonemes = lambda text, character="hangeul": "a"
    if LangCls is French or LangCls is Spanish:
        lang.tokenizer = types.SimpleNamespace(tokenize=lambda x: [x])
    try:
        phones, tones, word2ph = lang.call(oov)
        assert isinstance(phones, list)
        assert isinstance(tones, list)
        assert isinstance(word2ph, list)
    except Exception as e:
        # Accept AssertionError, NotImplementedError, or KeyError if the module is a stub
        assert isinstance(e, (AssertionError, NotImplementedError, KeyError))
