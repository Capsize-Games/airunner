"""
Unit tests for melo.text.chinese

Covers: text_normalize, call, _g2p, and edge/error cases.
"""

import pytest
from airunner.vendor.melo.text.chinese import Chinese


def test_text_normalize_basic():
    c = Chinese()
    out = c.text_normalize("你好，世界！")
    assert isinstance(out, str)
    assert "你好" in out


def test_call_valid_chinese():
    c = Chinese()
    # Should not raise for valid Chinese
    phones, tones, word2ph = c.call("你好")
    assert isinstance(phones, list)
    assert isinstance(tones, list)
    assert isinstance(word2ph, list)
    assert len(phones) == len(tones) == sum(word2ph)


def test_call_empty():
    c = Chinese()
    phones, tones, word2ph = c.call("")
    assert phones == ["_", "_"]
    assert tones == [0, 0]
    assert word2ph == [1, 1]


def test_call_non_chinese():
    c = Chinese()
    # Should raise AssertionError for non-Chinese input
    with pytest.raises(AssertionError):
        c.call("foo")


def test_g2p_edge_cases():
    c = Chinese()
    # _g2p expects a list of sentences
    phones, tones, word2ph = c._g2p([""])
    assert isinstance(phones, list)
    assert isinstance(tones, list)
    assert isinstance(word2ph, list)


def test_get_initials_finals():
    c = Chinese()
    initials, finals = c._get_initials_finals("你好")
    assert isinstance(initials, list)
    assert isinstance(finals, list)
