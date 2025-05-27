"""
Unit tests for melo.split_utils
Covers importability and basic function presence.
"""

import pytest
import airunner.vendor.melo.split_utils as split_utils


def test_module_importable():
    assert split_utils is not None


def test_split_sentence_latin():
    text = "Hello world! This is a test. Short. Another sentence, with commas."
    out = split_utils.split_sentences_latin(text)
    assert isinstance(out, list)
    assert any("test" in s for s in out)


def test_split_sentence_zh():
    text = "你好世界。这是一个测试。短句。另一个句子，带逗号。"
    out = split_utils.split_sentences_zh(text)
    assert isinstance(out, list)
    assert any("测试" in s for s in out)


def test_merge_short_sentences_en():
    sens = ["Hi.", "A test.", "Ok.", "This is a longer sentence."]
    out = split_utils.merge_short_sentences_en(sens)
    assert isinstance(out, list)
    assert any("longer" in s for s in out)


def test_merge_short_sentences_zh():
    sens = ["你好。", "测试。", "短。", "这是一个长句子。"]
    out = split_utils.merge_short_sentences_zh(sens)
    assert isinstance(out, list)
    assert any("长句子" in s for s in out)


def test_txtsplit_basic():
    text = "This is a sentence. This is another one! And a third? Short."
    out = split_utils.txtsplit(text, desired_length=10, max_length=30)
    assert isinstance(out, list)
    assert any("sentence" in s for s in out)
    # Should not split inside quotes
    text = 'He said, "This is quoted. Still quoted." And then more.'
    out = split_utils.txtsplit(text, desired_length=10, max_length=30)
    assert any("quoted" in s for s in out)


def test_split_sentence_dispatch():
    text = "Hello world! This is a test."
    out = split_utils.split_sentence(text, min_len=5)
    assert isinstance(out, list)

    # Test with AvailableLanguage.ZH
    class DummyLang:
        EN = "en"
        FR = "fr"
        ES = "es"
        SP = "sp"
        ZH = "zh"

    out = split_utils.split_sentence(
        "你好世界。这是一个测试。", min_len=5, language=DummyLang.ZH
    )
    assert isinstance(out, list)
