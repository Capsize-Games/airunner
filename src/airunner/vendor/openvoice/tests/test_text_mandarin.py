"""
Unit tests for openvoice.text.mandarin
Covers importability and basic function presence.
"""

import pytest
import airunner.vendor.openvoice.text.mandarin as mandarin


def test_module_importable():
    assert mandarin is not None


def test_number_to_chinese():
    assert mandarin.number_to_chinese("我有2个苹果") == "我有二个苹果"
    assert mandarin.number_to_chinese("价格是3.5元") == "价格是三点五元"


def test_chinese_to_bopomofo():
    out = mandarin.chinese_to_bopomofo("你好，世界！")
    assert isinstance(out, str)
    assert len(out) > 0


def test_latin_to_bopomofo():
    assert "ㄅㄧˋ" in mandarin.latin_to_bopomofo("b")
    assert "ㄟˉ" in mandarin.latin_to_bopomofo("a")


def test_bopomofo_to_romaji():
    assert "p⁼wo" in mandarin.bopomofo_to_romaji("ㄅㄛ")
    assert "mwo" in mandarin.bopomofo_to_romaji("ㄇㄛ")


def test_bopomofo_to_ipa():
    assert "p⁼wo" in mandarin.bopomofo_to_ipa("ㄅㄛ")
    assert "aɪ" in mandarin.bopomofo_to_ipa("ㄞ")


def test_bopomofo_to_ipa2():
    assert "pwo" in mandarin.bopomofo_to_ipa2("ㄅㄛ")
    assert "aɪ" in mandarin.bopomofo_to_ipa2("ㄞ")


def test_chinese_to_romaji():
    out = mandarin.chinese_to_romaji("你好，世界！")
    assert isinstance(out, str)
    assert len(out) > 0


def test_chinese_to_lazy_ipa():
    out = mandarin.chinese_to_lazy_ipa("你好，世界！")
    assert isinstance(out, str)
    assert len(out) > 0


def test_chinese_to_ipa():
    out = mandarin.chinese_to_ipa("你好，世界！")
    assert isinstance(out, str)
    assert len(out) > 0


def test_chinese_to_ipa2():
    out = mandarin.chinese_to_ipa2("你好，世界！")
    assert isinstance(out, str)
    assert len(out) > 0
