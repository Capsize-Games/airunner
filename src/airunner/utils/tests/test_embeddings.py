"""
Unit tests for airunner.utils.art.embeddings.get_embeddings_by_version
Covers filtering logic and edge cases.
"""

import pytest
from unittest.mock import patch, MagicMock
from airunner.utils.art.embeddings import get_embeddings_by_version


def make_embedding(version):
    emb = MagicMock()
    emb.version = version
    return emb


@patch("airunner.utils.art.embeddings.Embedding")
def test_get_embeddings_by_version_filters_correctly(mock_embedding):
    emb1 = make_embedding("v1")
    emb2 = make_embedding("v2")
    emb3 = make_embedding("v1")
    mock_embedding.objects.all.return_value = [emb1, emb2, emb3]
    result = get_embeddings_by_version("v1")
    assert emb1 in result
    assert emb3 in result
    assert emb2 not in result
    assert all(e.version == "v1" for e in result)


@patch("airunner.utils.art.embeddings.Embedding")
def test_get_embeddings_by_version_empty(mock_embedding):
    mock_embedding.objects.all.return_value = []
    result = get_embeddings_by_version("v1")
    assert result == []


@patch("airunner.utils.art.embeddings.Embedding")
def test_get_embeddings_by_version_no_match(mock_embedding):
    emb1 = make_embedding("v2")
    mock_embedding.objects.all.return_value = [emb1]
    result = get_embeddings_by_version("v1")
    assert result == []
