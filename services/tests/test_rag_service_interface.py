"""Conformance test for the ``RAGService`` port.

See ``airunner_services/llm/rag_service.py``. The port names the RAG
operations the daemon calls, so that a caller can depend on a capability
rather than on ``LLMModelManager`` (which currently *is* the RAG manager).
This test pins the current implementation (``RAGMixin``) to the port, so the
interface and its implementation cannot drift apart unnoticed.
"""

from __future__ import annotations

import inspect

import pytest

# RAGMixin pulls in torch/langchain, only installed with the llm-native
# extra. Skip cleanly on the lean CI install rather than erroring at import.
pytest.importorskip("torch")
pytest.importorskip("langchain_core")

from airunner_services.llm.rag_mixin import RAGMixin  # noqa: E402
from airunner_services.llm.rag_service import (  # noqa: E402
    RAG_SERVICE_METHODS,
    RAGService,
)


def test_method_list_matches_the_protocol_surface() -> None:
    """RAG_SERVICE_METHODS must stay in sync with the protocol class."""
    protocol_methods = {
        name for name in dir(RAGService) if not name.startswith("_")
    }
    assert protocol_methods == set(RAG_SERVICE_METHODS)


def test_every_ported_method_exists_on_rag_mixin() -> None:
    """Each ported operation is callable on the current implementation."""
    missing = [
        name
        for name in RAG_SERVICE_METHODS
        if not callable(getattr(RAGMixin, name, None))
    ]
    assert missing == []


def test_rag_mixin_satisfies_the_rag_service_protocol() -> None:
    """RAGMixin is a structural RAGService (method presence)."""
    assert issubclass(RAGMixin, RAGService)


def test_protocol_parameters_are_accepted_by_the_implementation() -> None:
    """The implementation accepts every parameter the port declares.

    Runtime-checkable protocols do not check signatures, so this guards the
    port against a rename or a dropped keyword the port advertises.
    """
    problems: list[tuple[str, list[str]]] = []
    for name in RAG_SERVICE_METHODS:
        protocol_signature = inspect.signature(getattr(RAGService, name))
        implementation_signature = inspect.signature(getattr(RAGMixin, name))
        implementation_parameters = set(implementation_signature.parameters)
        missing = [
            parameter
            for parameter in protocol_signature.parameters
            if parameter != "self" and parameter not in implementation_parameters
        ]
        if missing:
            problems.append((name, missing))
    assert problems == []
