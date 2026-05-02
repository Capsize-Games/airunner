"""Tests for streamed text normalization helpers."""

from airunner.components.llm.utils.stream_text import combine_stream_chunks


def test_combine_stream_chunks_inserts_word_boundary_spaces():
    """Adjacent word chunks should remain readable."""
    assert combine_stream_chunks(["Hello", "world", "!"]) == "Hello world!"


def test_combine_stream_chunks_preserves_existing_spacing():
    """Existing whitespace in streamed chunks should be preserved."""
    assert combine_stream_chunks(["Hello", " world"]) == "Hello world"


def test_combine_stream_chunks_keeps_code_like_boundaries_tight():
    """Code-style punctuation should not gain extra spaces."""
    assert combine_stream_chunks(["print", "(", '"hi"', ")"]) == 'print("hi")'