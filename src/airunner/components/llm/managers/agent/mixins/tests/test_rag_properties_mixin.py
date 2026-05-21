"""Unit tests for local-only RAG embedding metadata preflight."""

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

from airunner.components.llm.managers.agent.mixins import (
    rag_properties_mixin as module,
)
from airunner.components.llm.managers.agent.mixins.rag_properties_mixin import (
    RAGPropertiesMixin,
)


class _DummyRAGPropertiesMixin(RAGPropertiesMixin):
    def __init__(self, base_path: Path):
        self.logger = Mock()
        self.path_settings = SimpleNamespace(base_path=str(base_path))
        self._embedding = None
        self._text_splitter = None
        self._index_registry = None
        self._target_files = None

    def _check_and_download_embedding_model(self, _model_path: str) -> bool:
        return True


def test_embedding_creates_local_sentence_transformer_metadata(monkeypatch, tmp_path):
    """Embedding init should not require hub fallback for optional metadata."""
    model_dir = (
        tmp_path / "text" / "models" / "llm" / "embedding" / "intfloat" / "e5-large"
    )
    model_dir.mkdir(parents=True)

    created = {}

    class _FakeEmbeddings:
        def __init__(self, **kwargs):
            created.update(kwargs)

    monkeypatch.setattr(module, "HuggingFaceEmbeddings", _FakeEmbeddings)
    monkeypatch.setattr(module.torch.cuda, "is_available", lambda: False)
    monkeypatch.setattr(
        module.torch.backends,
        "mps",
        SimpleNamespace(is_available=lambda: False),
        raising=False,
    )

    mixin = _DummyRAGPropertiesMixin(tmp_path)

    embedding = mixin.embedding

    assert isinstance(embedding, module._PrefixedEmbeddingAdapter)
    assert created["model_name"] == str(model_dir)
    assert created["model_kwargs"]["local_files_only"] is True
    assert (model_dir / "config_sentence_transformers.json").read_text(
        encoding="utf-8"
    ) == '{\n  "__version__": {}\n}\n'
    assert (model_dir / "README.md").read_text(encoding="utf-8") == (
        "# intfloat/e5-large\n"
    )


def test_embedding_adapter_prefixes_e5_queries_and_passages(
    monkeypatch,
    tmp_path,
):
    """E5 embeddings should receive the required query/passage prefixes."""
    model_dir = (
        tmp_path / "text" / "models" / "llm" / "embedding" / "intfloat" / "e5-large"
    )
    model_dir.mkdir(parents=True)

    calls = {"queries": [], "documents": []}

    class _FakeEmbeddings:
        def __init__(self, **_kwargs):
            pass

        def embed_query(self, text):
            calls["queries"].append(text)
            return [1.0]

        def embed_documents(self, texts):
            calls["documents"].append(list(texts))
            return [[1.0] for _text in texts]

    monkeypatch.setattr(module, "HuggingFaceEmbeddings", _FakeEmbeddings)
    monkeypatch.setattr(module.torch.cuda, "is_available", lambda: False)
    monkeypatch.setattr(
        module.torch.backends,
        "mps",
        SimpleNamespace(is_available=lambda: False),
        raising=False,
    )

    mixin = _DummyRAGPropertiesMixin(tmp_path)

    embedding = mixin.embedding
    embedding.embed_query("who is the detective?")
    embedding.embed_documents(["A detective inspects the cemetery."])

    assert calls["queries"] == ["query: who is the detective?"]
    assert calls["documents"] == [
        ["passage: A detective inspects the cemetery."]
    ]