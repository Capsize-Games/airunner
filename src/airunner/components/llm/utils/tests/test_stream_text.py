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


def test_combine_stream_chunks_preserves_spaces_in_named_entities():
    """Title-and-name boundaries should stay readable in prose."""
    assert combine_stream_chunks(["Miss", "Marple"]) == "Miss Marple"


def test_combine_stream_chunks_preserves_spaces_between_common_words():
    """Plain prose chunks should not collapse into one token."""
    assert combine_stream_chunks(["some", "details"]) == "some details"


def test_combine_stream_chunks_preserves_single_letter_word_boundaries():
    """Single-letter words should remain separate from neighbors."""
    assert combine_stream_chunks(["involves", "a"]) == "involves a"
    assert combine_stream_chunks(["a", "specific"]) == "a specific"


def test_combine_stream_chunks_preserves_spaces_before_titles():
    """Honorifics should keep their word boundary."""
    assert combine_stream_chunks(["is", "Mr."]) == "is Mr."


def test_combine_stream_chunks_preserves_spaces_in_place_names():
    """Multi-word place names should not collapse during streaming."""
    assert combine_stream_chunks(["West", "Indies"]) == "West Indies"


def test_combine_stream_chunks_repairs_whodunit_split_boundary():
    """Whodunit should keep the outer space but drop the inner split."""
    assert (
        combine_stream_chunks(["classic", "whod", " unit"])
        == "classic whodunit"
    )


def test_combine_stream_chunks_preserves_space_for_a_caribbean_title():
    """Single-letter titles should still keep their word boundary."""
    assert combine_stream_chunks(["A", "Caribbean"]) == "A Caribbean"


def test_combine_stream_chunks_preserves_space_in_agatha_christie_name():
    """Proper names split across chunks should remain readable."""
    assert (
        combine_stream_chunks(["Ag", " atha", "Christie"])
        == "Agatha Christie"
    )


def test_combine_stream_chunks_preserves_space_before_doctor_title():
    """Common honorifics should keep a boundary in prose."""
    assert combine_stream_chunks(["like", "Dr."]) == "like Dr."


def test_combine_stream_chunks_preserves_common_prose_boundaries():
    """Readable prose should keep simple verb and noun boundaries."""
    assert combine_stream_chunks(["to", "see"]) == "to see"
    assert combine_stream_chunks(["keen", "observations"]) == (
        "keen observations"
    )


def test_combine_stream_chunks_restores_recent_prose_regressions():
    """Recent streamed prose boundaries should not collapse."""
    assert combine_stream_chunks(["I'm", "still", "a", "bit"]) == (
        "I'm still a bit"
    )
    assert combine_stream_chunks(["search results", "I"]) == (
        "search results I"
    )
    assert combine_stream_chunks(["a", "mystery"]) == "a mystery"
    assert combine_stream_chunks(["a", "conversation"]) == (
        "a conversation"
    )
    assert combine_stream_chunks(["a", '"snapshot']) == 'a "snapshot'
    assert combine_stream_chunks(["book", "2"]) == "book 2"
    assert combine_stream_chunks(["name", "(if"]) == "name (if"
    assert combine_stream_chunks(["Once", "I"]) == "Once I"


def test_combine_stream_chunks_merges_red_herrings_suffix_split():
    """Red-herring style suffix splits should collapse back into one word."""
    assert combine_stream_chunks(["redherr", " ings"]) == "redherrings"