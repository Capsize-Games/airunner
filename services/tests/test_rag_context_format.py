"""Unit tests for rag_tools._format_rag_context.

The context formatter was extracted to keep rag_search within the
long-function threshold. These tests pin excerpt truncation, source
labels, and joining behavior.
"""

from types import SimpleNamespace

from airunner_services.llm.tools.rag_tools import _format_rag_context


def _doc(content, source="file.txt"):
    return SimpleNamespace(page_content=content, metadata={"source": source})


def test_single_result_format():
    out = _format_rag_context([_doc("hello world")])
    assert out == "[Source 1: file.txt]\nhello world"


def test_truncates_long_content_at_limit():
    out = _format_rag_context([_doc("x" * 900)])
    assert "[Source 1: file.txt]\n" in out
    body = out.split("\n", 1)[1]
    assert len(body) == 500


def test_exact_limit_content_not_truncated():
    content = "y" * 500
    out = _format_rag_context([_doc(content)])
    assert out.endswith(content)


def test_multiple_results_numbered_and_joined():
    out = _format_rag_context([_doc("a", "f1"), _doc("b", "f2")])
    assert out == "[Source 1: f1]\na\n\n[Source 2: f2]\nb"


def test_missing_source_defaults_to_unknown():
    doc = SimpleNamespace(page_content="c", metadata={})
    out = _format_rag_context([doc])
    assert out == "[Source 1: unknown]\nc"
