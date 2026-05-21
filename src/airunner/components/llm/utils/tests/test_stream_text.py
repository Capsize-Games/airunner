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


def test_combine_stream_chunks_inserts_missing_word_boundary_space():
    """Readable prose should recover spaces between full word chunks."""
    assert combine_stream_chunks(["Hello", "world"]) == "Hello world"


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


def test_combine_stream_chunks_handles_markdown_title_boundaries():
    """Markdown emphasis should keep surrounding boundaries readable."""
    assert (
        combine_stream_chunks(
            [
                "According",
                "to",
                "*The",
                "Sat",
                " anic",
                "Bible*",
                "by",
                "Anton",
                "La",
                "Vey,",
            ]
        )
        == "According to *The Satanic Bible* by Anton LaVey,"
    )


def test_combine_stream_chunks_removes_spurious_subword_leading_space():
    """Subword continuations should drop bogus leading spaces."""
    assert combine_stream_chunks(["Sat", " anic"]) == "Satanic"


def test_combine_stream_chunks_preserves_short_common_word_boundaries():
    """Short standalone words should not collapse into their neighbors."""
    assert (
        combine_stream_chunks(
            [
                "Based",
                "on",
                "the",
                "document,",
                "it",
                "appears",
                "to",
                "be",
                "a",
                "story",
                "set",
                "in",
                "two",
                "worlds.",
            ]
        )
        == "Based on the document, it appears to be a story set in two worlds."
    )


def test_combine_stream_chunks_preserves_model_emitted_spaces():
    """Model-emitted leading spaces should survive normal prose updates."""
    assert (
        combine_stream_chunks(
            [
                "Based",
                " on",
                " the",
                " document",
                ",",
                " it",
                " appears",
                " to",
                " be",
                " a",
                " story",
            ]
        )
        == "Based on the document, it appears to be a story"
    )


def test_combine_stream_chunks_restores_common_word_boundaries():
    """Common prose chunks should recover missing spaces between words."""
    assert combine_stream_chunks(["car", "accident"]) == "car accident"


def test_combine_stream_chunks_removes_split_word_suffix_spaces():
    """Split-word suffix fragments should stay attached to the base word."""
    assert combine_stream_chunks(["melanch", " olic"]) == "melancholic"


def test_combine_stream_chunks_drops_space_after_opening_quote():
    """Opening quotes should not keep an extra interior leading space."""
    assert (
        combine_stream_chunks(["He said", ' "', " hello", '"'])
        == 'He said "hello"'
    )


def test_combine_stream_chunks_restores_missing_space_between_plain_words():
    """Common lowercase words should not collapse into one token."""
    assert combine_stream_chunks(["now", "seems"]) == "now seems"


def test_combine_stream_chunks_removes_split_ibility_space():
    """Split words ending in -ibility should stay contiguous."""
    assert combine_stream_chunks(["imposs", " ibility"]) == "impossibility"


def test_combine_stream_chunks_preserves_space_after_possessive_word():
    """Possessive words should still keep a boundary before the next word."""
    assert combine_stream_chunks(["writer's", "career"]) == "writer's career"


def test_combine_stream_chunks_preserves_space_after_split_possessive():
    """Possessive suffix chunks should attach left without collapsing right."""
    assert (
        combine_stream_chunks(["The narrator", "'s", "career"])
        == "The narrator's career"
    )


def test_combine_stream_chunks_removes_split_pective_space():
    """Split words ending in -pective should stay contiguous."""
    assert combine_stream_chunks(["intros", " pective"]) == "introspective"