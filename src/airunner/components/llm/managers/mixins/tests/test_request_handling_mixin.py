"""Unit tests for RequestHandlingMixin RAG preparation."""

from types import SimpleNamespace
from unittest.mock import Mock

from airunner.components.llm.managers.mixins.request_handling_mixin import (
    RequestHandlingMixin,
)


class _DummyRequestHandlingMixin(RequestHandlingMixin):
    def __init__(self):
        self.logger = Mock()
        self.ensure_indexed_files = Mock(return_value=False)


def test_prepare_request_rag_returns_retry_error_for_embedding_download():
    """Attached-doc requests should pause until embeddings finish."""
    mixin = _DummyRequestHandlingMixin()
    mixin._rag_retry_after_download = True
    mixin._last_rag_index_error = "Embedding model download in progress."
    llm_request = SimpleNamespace(rag_files=["/tmp/doc.pdf"])

    result = mixin._prepare_request_rag({}, llm_request, ["rag"])

    mixin.ensure_indexed_files.assert_called_once_with(["/tmp/doc.pdf"])
    assert result == {
        "response": (
            "Error: the embedding model required for document search is "
            "still downloading. AIRunner will retry your request "
            "automatically when the download finishes."
        ),
        "error": "Embedding model download in progress.",
        "retry_after_download": True,
    }