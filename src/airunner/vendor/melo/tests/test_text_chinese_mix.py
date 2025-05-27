"""
Unit tests for melo.text.chinese_mix

Note: No test in this file should launch a GUI. Remove or skip any test that launches a GUI application.
This file should not launch QApplication, QMainWindow, or any GUI.
"""

import re
import sys
import pytest
import airunner.vendor.melo.text.chinese_mix as chinese_mix_mod
from airunner.vendor.melo.text.chinese_mix import ChineseMix


@pytest.fixture(autouse=True)
def patch_languagebase_api(monkeypatch):
    class DummyAPI:
        logger = None
        paths = {"": "", None: ""}

        def __call__(self):
            return self

    monkeypatch.setattr("airunner.vendor.melo.text.language_base.API", DummyAPI)
    monkeypatch.setattr(sys, "exit", lambda *a, **kw: None)
    # Patch language_tone_start_map to include EN for English branch
    monkeypatch.setattr(chinese_mix_mod, "language_tone_start_map", {"EN": 0, "ZH": 10})


@pytest.fixture
def fake_pinyin_map(tmp_path, monkeypatch):
    fake_path = tmp_path / "opencpop-strict.txt"
    fake_path.write_text("a\tA\nb\tB\nbui\tBUI\nying\tYING\n", encoding="utf-8")
    monkeypatch.setattr(ChineseMix, "current_file_path", str(tmp_path))
    return str(fake_path)


@pytest.fixture
def fake_tone_sandhi(monkeypatch):
    class DummyTone:
        def pre_merge_for_modify(self, seg_cut):
            return seg_cut

        def modified_tone(self, word, pos, finals):
            return finals

    monkeypatch.setattr(chinese_mix_mod, "ToneSandhi", lambda: DummyTone())
    return DummyTone()


@pytest.fixture
def fake_jieba(monkeypatch):
    monkeypatch.setattr(chinese_mix_mod.psg, "lcut", lambda seg: [(seg, "n")])


@pytest.fixture
def fake_english(monkeypatch):
    class DummyEnglish:
        def call(self, text=None, pad_start_end=False, tokenized=None):
            return ["EN"], [1], [1]

    monkeypatch.setattr(chinese_mix_mod, "English", lambda: DummyEnglish())
    return DummyEnglish()


@pytest.fixture
def fake_chinese(monkeypatch):
    class DummyChinese:
        def call(self, text):
            return ["ZH"], [2], [1]

    monkeypatch.setattr(chinese_mix_mod, "Chinese", lambda: DummyChinese())
    return DummyChinese()


def test_module_importable():
    assert chinese_mix_mod is not None


def test_replace_punctuation_basic(fake_pinyin_map, fake_tone_sandhi):
    c = ChineseMix()
    text = "你好，world!\nabc123"
    out = c.replace_punctuation(text)
    # Should keep Chinese, English, and mapped punctuation only
    allowed = set(c.rep_map.values()).union(set(c.punctuation))
    invalid = [
        ch
        for ch in out
        if not (
            ("\u4e00" <= ch <= "\u9fff")
            or ("a" <= ch <= "z")
            or ("A" <= ch <= "Z")
            or ch in allowed
            or ch == " "
        )
    ]
    assert not invalid
    assert "abc123" not in out


def test_text_normalize_numbers_and_punct(fake_pinyin_map, fake_tone_sandhi):
    c = ChineseMix()
    text = "我有2个apple，价格是3.5元。"
    out = c.text_normalize(text)
    assert "二" in out and "三点五" in out
    assert any(p in out for p in c.punctuation)


def test_call_v2_english_and_chinese(
    fake_pinyin_map, fake_tone_sandhi, fake_english, fake_chinese
):
    c = ChineseMix()
    c.tokenizer = type("DummyTokenizer", (), {"tokenize": lambda self, x: [x]})()
    text = "hello世界"
    phones, tones, word2ph = c.call(text, impl="v2")
    assert "EN" in phones and "ZH" in phones
    assert 1 in tones and 2 in tones
    assert sum(word2ph) == len(phones)


def test_call_v1_g2p_branches(
    fake_pinyin_map, fake_tone_sandhi, fake_jieba, fake_english
):
    c = ChineseMix()
    c.tokenizer = type("DummyTokenizer", (), {"tokenize": lambda self, x: [x]})()
    c.pinyin_to_symbol_map = {"a": "A", "b": "B"}
    c._get_initials_finals = lambda word: (["a", "b"], ["1", "1"])
    c.tone_modifier.modified_tone = lambda w, p, f: f
    # Patch English.call to return dummy values
    c.english.call = lambda **kwargs: (["EN"], [1], [1])
    # Patch tokenizer to avoid real tokenization
    c.tokenizer.tokenize = lambda x: [x]
    # Patch jieba to always return a non-empty result
    chinese_mix_mod.psg.lcut = lambda seg: [("ab", "n")]
    phones, tones, word2ph = c.call("ab", impl="v1")
    assert phones == ["_", "A", "B", "_"] or "EN" in phones
    assert sum(word2ph) == len(phones)


def test_call_invalid_impl(fake_pinyin_map, fake_tone_sandhi):
    c = ChineseMix()
    with pytest.raises(NotImplementedError):
        c.call("test", impl="invalid")


def test_replace_punctuation_edge_cases(fake_pinyin_map, fake_tone_sandhi):
    c = ChineseMix()
    assert c.replace_punctuation("") == ""
    assert c.replace_punctuation("123abc!@#") == "abc!"


def test_text_normalize_empty(fake_pinyin_map, fake_tone_sandhi):
    c = ChineseMix()
    assert c.text_normalize("") == ""
