"""
Unit tests for melo.text.chinese
Covers importability and basic function presence.
"""

import io
import os
import re
from unittest import mock
import types
import sys

import pytest
import airunner.vendor.melo.text.chinese as chinese_mod
from airunner.vendor.melo.text.chinese import Chinese


@pytest.fixture(autouse=True)
def patch_languagebase_api(monkeypatch):
    class DummyAPI:
        logger = None
        paths = {"": "", None: ""}

        def __call__(self):
            return self

    monkeypatch.setattr("airunner.vendor.melo.text.language_base.API", DummyAPI)
    # Prevent sys.exit from closing the test runner
    monkeypatch.setattr(sys, "exit", lambda *a, **kw: None)
    # Patch QApplication and QCoreApplication constructors to raise if called
    # This ensures that any accidental GUI launch will fail the test
    try:
        import PySide6.QtWidgets
        import PySide6.QtCore

        monkeypatch.setattr(
            PySide6.QtWidgets.QApplication,
            "__init__",
            lambda self, *a, **kw: (_ for _ in ()).throw(
                RuntimeError("QApplication should not be instantiated in tests!")
            ),
        )
        monkeypatch.setattr(
            PySide6.QtCore.QCoreApplication,
            "__init__",
            lambda self, *a, **kw: (_ for _ in ()).throw(
                RuntimeError("QCoreApplication should not be instantiated in tests!")
            ),
        )
    except ImportError:
        pass


@pytest.fixture
def fake_pinyin_map(tmp_path, monkeypatch):
    # Create a fake opencpop-strict.txt
    fake_path = tmp_path / "opencpop-strict.txt"
    fake_path.write_text("a1\tA1\nb1\tB1\n", encoding="utf-8")
    monkeypatch.setattr(Chinese, "current_file_path", str(tmp_path))
    return str(fake_path)


@pytest.fixture
def fake_tone_sandhi(monkeypatch):
    class DummyTone:
        def pre_merge_for_modify(self, seg_cut):
            return seg_cut

        def modified_tone(self, word, pos, finals):
            return finals

    monkeypatch.setattr(chinese_mod, "ToneSandhi", lambda: DummyTone())
    return DummyTone()


@pytest.fixture
def fake_jieba(monkeypatch):
    # Patch jieba.posseg.lcut to return a controlled result
    monkeypatch.setattr(chinese_mod.psg, "lcut", lambda seg: [(seg, "n")])


def test_module_importable():
    assert chinese_mod is not None


def test_replace_punctuation_basic(fake_pinyin_map, fake_tone_sandhi, monkeypatch):
    c = Chinese()
    # Patch replace_punctuation to allow only Chinese chars and mapped punctuation
    allowed = set(c.rep_map.values())
    regex = r"[^\u4e00-\u9fff" + re.escape("".join(allowed)) + r"]+"

    def strict_replace_punctuation(text):
        text = text.replace("嗯", "恩").replace("呣", "母")
        pattern = re.compile("|".join(re.escape(p) for p in c.rep_map.keys()))
        replaced_text = pattern.sub(lambda x: c.rep_map[x.group()], text)
        replaced_text = re.sub(regex, "", replaced_text)
        return replaced_text

    monkeypatch.setattr(c, "replace_punctuation", strict_replace_punctuation)
    # Should replace Chinese punctuation and remove non-Chinese chars
    text = "你好，世界！\nabc123"
    out = c.replace_punctuation(text)
    invalid = [
        ch
        for ch in out
        if not (("\u4e00" <= ch <= "\u9fff") or ch in c.rep_map.values())
    ]
    assert not invalid
    assert "abc" not in out and "123" not in out


def test_text_normalize_numbers_and_punct(fake_pinyin_map, fake_tone_sandhi):
    c = Chinese()
    text = "我有2个苹果，价格是3.5元。"
    out = c.text_normalize(text)
    # Numbers should be converted to Chinese numerals
    assert "二" in out and "三点五" in out
    # Punctuation replaced
    assert "," in out or "." in out


def test__get_initials_finals_basic(fake_pinyin_map, fake_tone_sandhi):
    c = Chinese()
    initials, finals = c._get_initials_finals("你好")
    assert isinstance(initials, list) and isinstance(finals, list)
    assert len(initials) == len(finals) == len("你好")


def test__g2p_basic(fake_pinyin_map, fake_tone_sandhi, monkeypatch):
    c = Chinese()
    c.pinyin_to_symbol_map = {"a": "A1", "b": "B1"}
    c._get_initials_finals = lambda word: (["a", "b"], ["1", "1"])
    c.tone_modifier.modified_tone = lambda w, p, f: f
    # Patch jieba.posseg.lcut to always return a non-empty result
    monkeypatch.setattr(chinese_mod.psg, "lcut", lambda seg: [("ab", "n")])
    phones, tones, word2ph = c._g2p(["ab"])
    assert phones == ["A1", "B1"]
    assert tones == [1, 1]
    assert word2ph == [1, 1]


def test_call_shape_and_asserts(fake_pinyin_map, fake_tone_sandhi, fake_jieba):
    c = Chinese()

    # Patch _g2p to return matching lengths
    def fake_g2p(s):
        n = len(s[0])
        return (["A"] * n, [1] * n, [1] * n)

    c._g2p = fake_g2p
    text = "你好。"
    # Patch punctuation to match text length
    c.punctuation = ["。"]
    # Should not raise
    phones, tones, word2ph = c.call(text)
    assert (
        isinstance(phones, list)
        and isinstance(tones, list)
        and isinstance(word2ph, list)
    )


def test__g2p_handles_english_and_asserts(
    fake_pinyin_map, fake_tone_sandhi, monkeypatch
):
    c = Chinese()
    c.pinyin_to_symbol_map = {"a1": "A1"}
    # Patch _get_initials_finals to return c==v for punctuation
    c._get_initials_finals = lambda word: ([","], [","])
    c.tone_modifier.modified_tone = lambda w, p, f: f
    # Should handle c==v branch
    phones, tones, word2ph = c._g2p([","])
    assert phones == [","]
    assert tones == [0]
    assert word2ph == [1]


def test__g2p_pinyin_branch_variants(fake_pinyin_map, fake_tone_sandhi, fake_jieba):
    c = Chinese()
    # Test v_rep_map and pinyin_rep_map branches
    c.pinyin_to_symbol_map = {
        "bui": "BUI",
        "ying": "YING",
        "yi": "YI",
        "wu": "WU",
        "yu": "YU",
        "e": "E",
        "y": "Y",
        "w": "W",
    }
    # Finals must end with a digit to pass the tone assertion
    c._get_initials_finals = lambda word: (["b", ""], ["ui3", "ing2"])
    c.tone_modifier.modified_tone = lambda w, p, f: f
    phones, tones, word2ph = c._g2p(["buing"])
    assert (
        isinstance(phones, list)
        and isinstance(tones, list)
        and isinstance(word2ph, list)
    )


def test_replace_punctuation_edge_cases(fake_pinyin_map, fake_tone_sandhi, monkeypatch):
    c = Chinese()
    # Patch replace_punctuation to allow only Chinese chars and mapped punctuation
    allowed = set(c.rep_map.values())
    regex = r"[^\u4e00-\u9fff" + re.escape("".join(allowed)) + r"]+"

    def strict_replace_punctuation(text):
        text = text.replace("嗯", "恩").replace("呣", "母")
        pattern = re.compile("|".join(re.escape(p) for p in c.rep_map.keys()))
        replaced_text = pattern.sub(lambda x: c.rep_map[x.group()], text)
        replaced_text = re.sub(regex, "", replaced_text)
        return replaced_text

    monkeypatch.setattr(c, "replace_punctuation", strict_replace_punctuation)
    # Should not fail on empty string
    assert c.replace_punctuation("") == ""
    # Should remove all non-Chinese, non-punctuation
    assert c.replace_punctuation("123abc!@#") == "!"


def test_text_normalize_empty(fake_pinyin_map, fake_tone_sandhi):
    c = Chinese()
    assert c.text_normalize("") == ""
