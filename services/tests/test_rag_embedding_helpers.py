"""Unit tests for the embedding device/branch extraction helpers.

_select_embedding_device, _remote_embedding, and _local_embedding
were extracted to keep the embedding property within the
long-function threshold. These tests pin the device preference
and the verified-load mutation paths.
"""

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

import airunner_services.llm.managers.agent.mixins.rag_properties_mixin as mixin_mod
from airunner_services.llm.managers.agent.mixins.rag_properties_mixin import (
    RAGPropertiesMixin,
    _select_embedding_device,
)


def _make_obj():
    obj = RAGPropertiesMixin.__new__(RAGPropertiesMixin)
    obj.logger = MagicMock()
    return obj


def test_device_prefers_cuda(monkeypatch):
    monkeypatch.setattr(mixin_mod.torch.cuda, "is_available", lambda: True)
    assert _select_embedding_device() == "cuda"


def test_device_falls_back_to_mps(monkeypatch):
    monkeypatch.setattr(mixin_mod.torch.cuda, "is_available", lambda: False)
    monkeypatch.setattr(
        mixin_mod.torch.backends.mps, "is_available", lambda: True
    )
    assert _select_embedding_device() == "mps"


def test_device_defaults_cpu(monkeypatch):
    monkeypatch.setattr(mixin_mod.torch.cuda, "is_available", lambda: False)
    monkeypatch.setattr(
        mixin_mod.torch.backends.mps, "is_available", lambda: False
    )
    assert _select_embedding_device() == "cpu"


def test_remote_embedding_builds_ollama_client(monkeypatch):
    obj = _make_obj()
    ollama = MagicMock()
    monkeypatch.setitem(
        __import__("sys").modules, "langchain_ollama", ollama
    )
    ollama.OllamaEmbeddings.return_value = "client"
    assert obj._remote_embedding("http://x:11434") == "client"
    ollama.OllamaEmbeddings.assert_called_once()


def test_local_embedding_verifies_and_wraps(monkeypatch):
    obj = _make_obj()
    obj.path_settings = SimpleNamespace(base_path="/base")
    monkeypatch.setattr(
        "airunner_services.runtimes.e5_model_identity.verify_e5_model_directory",
        lambda path: "identity",
    )
    monkeypatch.setattr(mixin_mod, "HuggingFaceEmbeddings", lambda **kw: "raw")
    monkeypatch.setattr(
        "airunner_services.runtimes.e5_model_identity.VerifiedE5Embedder",
        lambda raw, identity, activity_lock: "wrapped",
    )
    monkeypatch.setattr(mixin_mod.torch.cuda, "is_available", lambda: False)
    assert obj._local_embedding() == "wrapped"


def test_local_embedding_none_when_verification_fails(monkeypatch):
    obj = _make_obj()
    obj.path_settings = SimpleNamespace(base_path="/base")
    import airunner_services.runtimes.e5_model_identity as identity_mod

    monkeypatch.setattr(
        identity_mod,
        "verify_e5_model_directory",
        MagicMock(side_effect=identity_mod.E5ModelIdentityError("bad")),
    )
    assert obj._local_embedding() is None
