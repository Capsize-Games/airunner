"""
Unit tests for melo.text.language_base

Covers: distribute_phone, unicode_normalize, device/model/tokenizer properties, dict loading, and abstract call.
"""

import os
import tempfile
import pickle
import pytest
from unittest import mock
from airunner.vendor.melo.text.language_base import LanguageBase


def test_distribute_phone_balanced():
    # Should distribute phones as evenly as possible
    assert LanguageBase.distribute_phone(4, 2) == [2, 2]
    assert LanguageBase.distribute_phone(5, 2) == [3, 2]
    assert LanguageBase.distribute_phone(0, 3) == [0, 0, 0]


def test_unicode_normalize():
    # Should normalize unicode text
    s = "ＡＢＣ１２３"
    norm = LanguageBase.unicode_normalize(s)
    assert norm == "ABC123"


def test_device_property(monkeypatch):
    lb = LanguageBase()
    monkeypatch.setattr("torch.backends.mps.is_available", lambda: False)
    monkeypatch.setattr("torch.cuda.is_available", lambda: False)
    assert lb.device == "cpu"
    monkeypatch.setattr("torch.cuda.is_available", lambda: True)
    assert lb.device == "cuda"
    monkeypatch.setattr("torch.backends.mps.is_available", lambda: True)
    assert lb.device == "mps"


def test_call_not_implemented():
    lb = LanguageBase()
    with pytest.raises(NotImplementedError):
        lb.call("foo")


def test_get_dict_and_cache(monkeypatch, tmp_path):
    lb = LanguageBase()
    # Patch file paths to use temp
    cache_path = tmp_path / "cache.pickle"
    dict_path = tmp_path / "dict.rep"
    lb.CACHE_PATH = str(cache_path)
    lb.CMU_DICT_PATH = str(dict_path)
    # Write a fake dict file in the expected format: WORD  PH0 - PH1
    with open(dict_path, "w") as f:
        for i in range(50):
            f.write(f"WORD{i}  PH0 - PH1\n")
    # Patch cache_dict to track calls
    called = {}

    def fake_cache_dict(d, path):
        called["cached"] = True
        with open(path, "wb") as pf:
            pickle.dump(d, pf)

    monkeypatch.setattr(lb, "cache_dict", fake_cache_dict)
    d = lb.get_dict()
    assert isinstance(d, dict)
    assert called["cached"]
    # Now test loading from cache
    d2 = lb.get_dict()
    assert d2 == d


def test_model_and_tokenizer_properties(monkeypatch):
    lb = LanguageBase()
    # Patch API().paths to return a dummy path at the import location used by LanguageBase
    monkeypatch.setattr(
        "airunner.vendor.melo.text.language_base.API",
        lambda: type("A", (), {"paths": {"": "dummy"}})(),
    )
    # Patch transformers loader at the import location used by LanguageBase
    monkeypatch.setattr(
        "airunner.vendor.melo.text.language_base.AutoModelForMaskedLM.from_pretrained",
        lambda *a, **k: mock.Mock(),
    )
    monkeypatch.setattr(
        "airunner.vendor.melo.text.language_base.AutoTokenizer.from_pretrained",
        lambda *a, **k: mock.Mock(),
    )
    # Should not raise
    _ = lb.bert_model_path
    _ = lb.bert_model
    _ = lb.bert_tokenizer
    _ = lb.model_id
    _ = lb.tokenizer
    lb.tokenizer = "foo"
    assert lb._tokenizer == "foo"
