"""Tests for streamed text normalization helpers."""

from airunner.components.llm.utils.stream_text import combine_stream_chunks


def test_combine_stream_chunks_keeps_subword_boundaries_tight():
    """Subword chunks should not gain spaces inside one word."""
    assert combine_stream_chunks(["Sat", "anic"]) == "Satanic"


def test_combine_stream_chunks_keeps_mixed_case_name_chunks_tight():
    """Name fragments should remain contiguous across chunk splits."""
    assert combine_stream_chunks(["La", "V", "ey"]) == "LaVey"


def test_combine_stream_chunks_preserves_existing_spacing():
    """Existing whitespace in streamed chunks should be preserved."""
    assert combine_stream_chunks(["Hello", " world"]) == "Hello world"


def test_combine_stream_chunks_keeps_code_like_boundaries_tight():
    """Code-style punctuation should not gain extra spaces."""
    assert combine_stream_chunks(["print", "(", '"hi"', ")"]) == 'print("hi")'


def test_combine_stream_chunks_inserts_space_after_sentence_punctuation():
    """Sentence-ending punctuation should keep following text separate."""
    assert (
        combine_stream_chunks(["How are you?", "Let me know"])
        == "How are you? Let me know"
    )


def test_combine_stream_chunks_inserts_spaces_around_emojis():
    """Emoji chunk boundaries should remain readable in prose."""
    assert (
        combine_stream_chunks(["Computer!", "😊", "How can I help?"])
        == "Computer! 😊 How can I help?"
    )