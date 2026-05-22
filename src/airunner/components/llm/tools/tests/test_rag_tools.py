"""Unit tests for RAG tool result formatting."""

import os
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock, patch

from airunner.components.llm.tools.rag_tools import (
    analyze_loaded_document,
    inspect_loaded_documents,
    rag_search,
    search_knowledge_base_documents,
    save_to_knowledge_base,
)


def _summary_request(focus: str = "overview") -> SimpleNamespace:
    """Return request metadata for summary-style document turns."""
    return SimpleNamespace(
        document_query_intent="summary",
        document_summary_focus=focus,
    )


def _build_session_with_active_docs(*doc_batches: list[object]) -> MagicMock:
    """Return a mocked session that yields active-doc batches."""
    session = MagicMock()
    query = session.query.return_value
    query.filter_by.return_value.all.side_effect = list(doc_batches)
    return session


def test_rag_search_returns_metadata_and_excerpts_for_document_queries():
    """RAG search should stay generic and always return evidence."""
    doc = SimpleNamespace(
        metadata={
            "source": "/library/The Satanic Bible - Anton LaVey.pdf",
            "file_name": "The Satanic Bible - Anton LaVey.pdf",
            "file_type": ".pdf",
            "file_path": "/library/The Satanic Bible - Anton LaVey.pdf",
        },
        page_content="Opening excerpt from the attached document.",
    )
    api = SimpleNamespace(search=lambda query, k=6: [doc])

    result = rag_search("what is this document?", api=api)

    assert "Matched documents:" in result
    assert "Relevant excerpts:" in result
    assert (
        "Document 1: The Satanic Bible - Anton LaVey.pdf" in result
    )
    assert (
        "Inferred title from filename: The Satanic Bible" in result
    )
    assert "Inferred author from filename: Anton LaVey" in result
    assert (
        "[Excerpt 1 from The Satanic Bible - Anton LaVey.pdf]" in result
    )


def test_rag_search_uses_summary_retrieval_breadth_from_request_metadata():
    """Summary breadth should come from request metadata, not query text."""
    doc = SimpleNamespace(
        metadata={
            "source": "/library/The Satanic Bible - Anton LaVey.pdf",
            "file_name": "The Satanic Bible - Anton LaVey.pdf",
            "file_type": ".pdf",
            "file_path": "/library/The Satanic Bible - Anton LaVey.pdf",
        },
        page_content="Opening excerpt from the attached document.",
    )
    search = Mock(return_value=[doc])
    api = SimpleNamespace(
        search=search,
        llm_request=_summary_request(),
        _get_active_document_names=lambda: [
            "The Satanic Bible - Anton LaVey.pdf"
        ],
    )

    rag_search("summarize the document for me", api=api)

    assert search.call_args.kwargs["k"] == 12


@patch("airunner.components.llm.tools.rag_tools.extract_text")
@patch("airunner.components.llm.tools.rag_tools.resolve_existing_file")
def test_rag_search_builds_summary_evidence_across_document(
    mock_resolve,
    mock_extract,
):
    """Summary intent should cover multiple document regions when possible."""
    file_path = "/library/The Satanic Bible - Anton LaVey.pdf"
    mock_resolve.return_value = file_path
    mock_extract.return_value = (
        "INTRODUCTION\n\n"
        "The introduction frames Satanism as a realism-first philosophy.\n\n"
        "THE BOOK OF SATAN\n\n"
        "This section rejects Christian mysticism and centers the real world.\n\n"
        "THE BOOK OF LUCIFER\n\n"
        "This section presents key arguments and practical philosophy.\n\n"
        "THE BOOK OF BELIAL\n\n"
        "This section focuses on ritual as applied practice.\n\n"
        "THE BOOK OF LEVIATHAN\n\n"
        "This section contains later material and ceremonial text."
    )
    search = Mock()
    api = SimpleNamespace(
        search=search,
        llm_request=_summary_request(),
        _get_active_document_paths=lambda: [file_path],
        _get_active_document_names=lambda: [
            "The Satanic Bible - Anton LaVey.pdf"
        ],
    )

    result = rag_search("summarize the document for me", api=api)

    assert "Current document: loaded document" in result
    assert "Matched documents:" not in result
    assert "Inferred title from filename:" not in result
    assert "[Excerpt 1 from" not in result
    assert "[Excerpt 1]" in result
    assert "Front matter (INTRODUCTION)." in result
    assert "Section: THE BOOK OF SATAN." in result
    assert "Section: THE BOOK OF BELIAL." in result
    assert "Section: THE BOOK OF LEVIATHAN." in result
    search.assert_not_called()


@patch("airunner.components.llm.tools.rag_tools.extract_text")
@patch("airunner.components.llm.tools.rag_tools.resolve_existing_file")
def test_rag_search_summary_avoids_opening_front_matter_bias(
    mock_resolve,
    mock_extract,
):
    """Summary evidence should not prefer the first intro anecdote."""
    file_path = "/library/The Satanic Bible - Anton LaVey.pdf"
    mock_resolve.return_value = file_path
    mock_extract.return_value = (
        "INTRODUCTION\n\n"
        "Anton LaVey was sixteen years old when he began the road to "
        "High Priesthood while playing organ in a carnival.\n\n"
        "The introduction frames the work as a realist philosophy rooted "
        "in the tangible world rather than spiritual promises.\n\n"
        "THE BOOK OF SATAN\n\n"
        "This section inverts Christian moral assumptions and praises "
        "strength over humility.\n\n"
        "THE BOOK OF LUCIFER\n\n"
        "This section develops the argument in practical and rhetorical "
        "terms.\n\n"
        "THE BOOK OF BELIAL\n\n"
        "This section focuses on ritual and applied practice.\n\n"
        "THE BOOK OF LEVIATHAN\n\n"
        "This section covers ceremony, symbolism, and later material."
    )
    api = SimpleNamespace(
        search=Mock(),
        llm_request=_summary_request(),
        _get_active_document_paths=lambda: [file_path],
        _get_active_document_names=lambda: [
            "The Satanic Bible - Anton LaVey.pdf"
        ],
    )

    result = rag_search("summarize the document for me", api=api)

    assert "Front matter (INTRODUCTION)." in result
    assert "realist philosophy rooted in the tangible world" in result
    assert "sixteen years old" not in result


@patch("airunner.components.llm.tools.rag_tools.extract_text")
@patch("airunner.components.llm.tools.rag_tools.resolve_existing_file")
def test_rag_search_book_about_query_prefers_premise_over_late_scene_noise(
    mock_resolve,
    mock_extract,
):
    """Book-about summaries should use premise hooks, not late-scene plot salad."""
    file_path = "/library/A Graveyard for Lunatics - Ray Bradbury.mobi"
    mock_resolve.return_value = file_path
    paragraphs = [
        "Maximus Films sits beside a cemetery, giving the story a haunted Hollywood setting.",
        "The narrator introduces a world where movie illusions and death seem to share the same streets.",
        "Halloween parties and studio politics frame the opening atmosphere.",
    ]
    paragraphs.extend(
        f"Early filler paragraph {index} about studio life and strange rumors."
        for index in range(4, 47)
    )
    paragraphs.append(
        "A body appears on the cemetery wall, forcing the narrator to confront a mystery tied to the studio's past."
    )
    paragraphs.append(
        "The narrator realizes James Charles Arbuthnot was supposedly killed years earlier, sharpening the central conflict."
    )
    paragraphs.extend(
        f"More filler paragraph {index} about routine production work."
        for index in range(49, 60)
    )
    paragraphs.append(
        "The characters drove through Madrid, Rome, and Calcutta on studio sets before stopping at a Bronx brownstone facade."
    )
    mock_extract.return_value = "\n\n".join(paragraphs)
    api = SimpleNamespace(
        search=Mock(),
        llm_request=_summary_request("premise"),
        _get_active_document_paths=lambda: [file_path],
        _get_active_document_names=lambda: [
            "A Graveyard for Lunatics - Ray Bradbury.mobi"
        ],
    )

    result = rag_search("what is this book about?", api=api)

    assert "Matched documents:" not in result
    assert "Inferred title from filename:" not in result
    assert "haunted Hollywood setting" in result
    assert "central conflict" in result
    assert "Madrid, Rome, and Calcutta" not in result


@patch("airunner.components.llm.tools.rag_tools.extract_text")
@patch("airunner.components.llm.tools.rag_tools.resolve_existing_file")
def test_rag_search_book_about_query_prefers_grounded_mystery_hooks(
    mock_resolve,
    mock_extract,
):
    """Premise evidence should favor grounded mystery hooks over eerie framing."""
    file_path = "/library/A Graveyard for Lunatics - Ray Bradbury.mobi"
    mock_resolve.return_value = file_path
    mock_extract.return_value = "\n\n".join(
        [
            "The city is described as if the living and the dead occupy neighboring realms.",
            "Anything could happen in this dreamlike studio town where cemetery walls meet movie lots.",
            "The atmosphere is eerie, theatrical, and full of memory.",
            "A supposedly dead studio figure appears on a wall, forcing the narrator into a mystery tied to the studio's past.",
            "The narrator remembers seeing the man years earlier on roller skates outside Maximus Films after a car accident.",
            "Movie illusions, studio tricks, and human schemes shape the unfolding investigation across the lot.",
        ]
    )
    api = SimpleNamespace(
        search=Mock(),
        llm_request=_summary_request("premise"),
        _get_active_document_paths=lambda: [file_path],
        _get_active_document_names=lambda: [
            "A Graveyard for Lunatics - Ray Bradbury.mobi"
        ],
    )

    result = rag_search("what is this book about?", api=api)

    assert "supposedly dead studio figure" in result
    assert "studio tricks, and human schemes" in result
    assert "living and the dead occupy neighboring realms" not in result


@patch("airunner.components.llm.tools.rag_tools.extract_text")
@patch("airunner.components.llm.tools.rag_tools.resolve_existing_file")
def test_rag_search_book_about_query_deprioritizes_stray_dialogue(
    mock_resolve,
    mock_extract,
):
    """Premise evidence should not elevate quoted accusations over the mystery."""
    file_path = "/library/A Graveyard for Lunatics - Ray Bradbury.mobi"
    mock_resolve.return_value = file_path
    mock_extract.return_value = "\n\n".join(
        [
            "Maximus Films sits beside a cemetery, giving the story a haunted Hollywood setting.",
            '"You write junk, you drink too much, and you still brood over the crash," someone says while recalling five people killed on the road.',
            "A supposedly dead studio magnate on the cemetery wall pulls the narrator into a murder mystery tied to the studio's past.",
            "The investigation turns toward studio corruption, special effects, makeup, and human schemes rather than a literal haunting.",
        ]
    )
    api = SimpleNamespace(
        search=Mock(),
        llm_request=_summary_request("premise"),
        _get_active_document_paths=lambda: [file_path],
        _get_active_document_names=lambda: [
            "A Graveyard for Lunatics - Ray Bradbury.mobi"
        ],
    )

    result = rag_search("what is this book about?", api=api)

    assert "supposedly dead studio magnate" in result
    assert "studio corruption, special effects, makeup, and human schemes" in result
    assert '"You write junk' not in result


@patch("airunner.components.llm.tools.rag_tools.extract_text")
@patch("airunner.components.llm.tools.rag_tools.resolve_existing_file")
def test_rag_search_book_about_query_skips_quote_only_opening_fallback(
    mock_resolve,
    mock_extract,
):
    """Quote-heavy openings should not displace the actual inciting case."""
    file_path = "/library/A Caribbean Mystery - Agatha Christie.epub"
    mock_resolve.return_value = file_path
    mock_extract.return_value = "\n\n".join(
        [
            '"Take all this business about Kenya," said Major Palgrave. "Lots of chaps gabbing away who know nothing about the place!"',
            "Mr. Jason Rafiel is a wealthy, semi-paralysed man who visits the West Indies every year.",
            "Miss Marple realizes that Major Palgrave has shown her a photograph of a murderer just before he is killed at the resort.",
            "Rafiel later becomes Miss Marple's wealthy ally, giving her room to investigate the crimes on the island.",
        ]
    )
    api = SimpleNamespace(
        search=Mock(),
        llm_request=_summary_request("premise"),
        _get_active_document_paths=lambda: [file_path],
        _get_active_document_names=lambda: [
            "A Caribbean Mystery - Agatha Christie.epub"
        ],
    )

    result = rag_search("what is this book about?", api=api)

    assert "photograph of a murderer" in result
    assert "wealthy ally" in result
    assert '"Take all this business about Kenya' not in result


@patch("airunner.components.llm.tools.rag_tools.extract_text")
@patch("airunner.components.llm.tools.rag_tools.resolve_existing_file")
def test_rag_search_book_about_query_ignores_substring_marker_false_positives(
    mock_resolve,
    mock_extract,
):
    """Premise markers should not fire inside unrelated words."""
    file_path = "/library/A Caribbean Mystery - Agatha Christie.epub"
    mock_resolve.return_value = file_path
    paragraphs = [
        "But the pattern was essentially the same. An elderly man who needed a listener so that he could relive happier days.",
        "Nobody had ever known why. Her eyes strayed to Mr. Rafter's table, where he looked like a wrinkled old bird of prey.",
    ]
    paragraphs.extend(
        f"Bridge paragraph {index} about resort life and ordinary conversation."
        for index in range(3, 132)
    )
    paragraphs.extend(
        [
            "Major Palgrave offers Miss Marple a photograph of a murderer at the resort just before he is killed.",
            "Miss Marple investigates the killing while Jason Rafiel becomes a wealthy ally on the island.",
        ]
    )
    mock_extract.return_value = "\n\n".join(paragraphs)
    api = SimpleNamespace(
        search=Mock(),
        llm_request=_summary_request("premise"),
        _get_active_document_paths=lambda: [file_path],
        _get_active_document_names=lambda: [
            "A Caribbean Mystery - Agatha Christie.epub"
        ],
    )

    result = rag_search("what is this book about?", api=api)

    assert "photograph of a murderer" in result
    assert "wealthy ally" in result
    assert "needed a listener" not in result
    assert "wrinkled old bird of prey" not in result


@patch("airunner.components.llm.tools.rag_tools.extract_text")
@patch("airunner.components.llm.tools.rag_tools.resolve_existing_file")
def test_rag_search_book_about_query_preserves_current_frame_setting(
    mock_resolve,
    mock_extract,
):
    """Premise evidence should keep the present-frame resort setting."""
    file_path = "/library/A Caribbean Mystery - Agatha Christie.epub"
    mock_resolve.return_value = file_path
    mock_extract.return_value = "\n\n".join(
        [
            "Major Palgrave drifts into old recollections about overseas postings and people he met years ago.",
            "He repeats a doctor's story about recognizing a killer from a photograph in another country.",
            "The reminiscence keeps circling through distant colonies and army gossip.",
            "At the Golden Palm resort on St. Honore, Miss Marple sits among the other guests and endures Major Palgrave's chatter.",
            "Before he can finish, Major Palgrave is distracted while trying to show Miss Marple a snapshot of a murderer.",
            "When he is found dead, Miss Marple begins investigating the killing among the hotel guests.",
        ]
    )
    api = SimpleNamespace(
        search=Mock(),
        llm_request=_summary_request("premise"),
        _get_active_document_paths=lambda: [file_path],
        _get_active_document_names=lambda: [
            "A Caribbean Mystery - Agatha Christie.epub"
        ],
    )

    result = rag_search("what is this book about?", api=api)

    assert "Golden Palm resort on St. Honore" in result
    assert "snapshot of a murderer" in result
    assert "distant colonies and army gossip" not in result


@patch("airunner.components.llm.tools.rag_tools.extract_text")
@patch("airunner.components.llm.tools.rag_tools.resolve_existing_file")
def test_rag_search_book_about_query_splits_long_mixed_paragraph(
    mock_resolve,
    mock_extract,
):
    """Long mixed paragraphs should still surface separate premise roles."""
    file_path = "/library/A Caribbean Mystery - Agatha Christie.epub"
    mock_resolve.return_value = file_path
    mock_extract.return_value = (
        "At the Golden Palm resort on St. Honore, Major Palgrave bores "
        "Miss Marple with stories about Kenya, India, and the North West "
        "Frontier until he suddenly tries to show her a snapshot of a "
        "murderer; before he can explain it, he is interrupted, a ball of "
        "wool drops, and later he is found dead, drawing Miss Marple into "
        "an investigation among the hotel guests."
    )
    api = SimpleNamespace(
        search=Mock(),
        llm_request=_summary_request("premise"),
        _get_active_document_paths=lambda: [file_path],
        _get_active_document_names=lambda: [
            "A Caribbean Mystery - Agatha Christie.epub"
        ],
    )

    result = rag_search("what is this book about?", api=api)

    assert result.count("[Excerpt ") >= 2
    assert "At the Golden Palm resort on St. Honore" in result
    assert "Inciting incident." in result
    assert "snapshot of a murderer" in result
    assert "investigation among the hotel guests" in result


@patch("airunner.components.llm.tools.rag_tools.extract_text")
@patch("airunner.components.llm.tools.rag_tools.resolve_existing_file")
def test_rag_search_book_about_query_prefers_premise_coverage_over_scene_management(
    mock_resolve,
    mock_extract,
):
    """Scene-management detail should not displace premise coverage."""
    file_path = "/library/A Caribbean Mystery - Agatha Christie.epub"
    mock_resolve.return_value = file_path
    mock_extract.return_value = "\n\n".join(
        [
            "At the Golden Palm resort on St. Honore, Miss Marple sits among the hotel guests while Major Palgrave corners her with stories from his travels.",
            "Molly rearranges table decorations, removes a knife, straightens a fork, resets a glass, and walks out to the terrace before dinner.",
            "The subject of murder comes up and Major Palgrave produces a snapshot, asking whether anyone would guess the man in the photograph was a killer.",
            "Major Palgrave keeps talking about Kenya, India, and the North West Frontier while Miss Marple listens politely and keeps hold of her ball of wool.",
            "When Palgrave dies before he can explain the photograph, Miss Marple begins investigating the killing among the resort guests.",
        ]
    )
    api = SimpleNamespace(
        search=Mock(),
        llm_request=_summary_request("premise"),
        _get_active_document_paths=lambda: [file_path],
        _get_active_document_names=lambda: [
            "A Caribbean Mystery - Agatha Christie.epub"
        ],
    )

    result = rag_search("what is this book about?", api=api)

    assert "Golden Palm resort on St. Honore" in result
    assert "snapshot" in result
    assert "investigating the killing among the resort guests" in result
    assert "rearranges table decorations" not in result


@patch("airunner.components.llm.tools.rag_tools.extract_text")
@patch("airunner.components.llm.tools.rag_tools.resolve_existing_file")
def test_analyze_loaded_document_premise_theme_query_uses_premise_evidence(
    mock_resolve,
    mock_extract,
):
    """Whole-document analysis should keep premise/theme queries on the premise path."""
    file_path = "/library/A Caribbean Mystery - Agatha Christie.epub"
    mock_resolve.return_value = file_path
    mock_extract.return_value = "\n\n".join(
        [
            "At the Golden Palm resort on St. Honore, Miss Marple sits among the hotel guests while Major Palgrave corners her with stories from his travels.",
            '"Take all this business about Kenya," said Major Palgrave. "Lots of chaps gabbing away who know nothing about the place!"',
            "The subject of murder comes up and Major Palgrave produces a snapshot, asking whether anyone would guess the man in the photograph was a killer.",
            "When Palgrave dies before he can explain the photograph, Miss Marple begins investigating the killing among the resort guests.",
        ]
    )
    api = SimpleNamespace(
        llm_request=SimpleNamespace(
            document_query_intent="summary",
            document_summary_focus="premise",
            attached_document_total_tokens=9000,
            attached_document_capabilities=[
                {
                    "path": file_path,
                    "fits_current_context": False,
                }
            ],
        ),
        _get_active_document_paths=lambda: [file_path],
        _get_active_document_names=lambda: [
            "A Caribbean Mystery - Agatha Christie.epub"
        ],
    )

    result = analyze_loaded_document(
        "What is the premise and theme of this book?",
        api=api,
    )

    assert "Analysis mode: chunked_document" in result
    assert "Supporting evidence:" in result

    supporting_evidence = result.split("Supporting evidence:\n\n", 1)[1]
    assert "Golden Palm resort on St. Honore" in supporting_evidence
    assert "snapshot" in supporting_evidence
    assert "investigating the killing among the resort guests" in (
        supporting_evidence
    )
    assert '"Take all this business about Kenya' not in supporting_evidence


@patch("airunner.components.llm.tools.rag_tools.extract_text")
@patch("airunner.components.llm.tools.rag_tools.resolve_existing_file")
def test_analyze_loaded_document_explain_premise_query_uses_premise_evidence(
    mock_resolve,
    mock_extract,
):
    """Explain-premise phrasing should use the same premise evidence path."""
    file_path = "/library/A Caribbean Mystery - Agatha Christie.epub"
    mock_resolve.return_value = file_path
    mock_extract.return_value = "\n\n".join(
        [
            "At the Golden Palm resort on St. Honore, Miss Marple sits among the hotel guests while Major Palgrave corners her with stories from his travels.",
            '"Take all this business about Kenya," said Major Palgrave. "Lots of chaps gabbing away who know nothing about the place!"',
            "The subject of murder comes up and Major Palgrave produces a snapshot, asking whether anyone would guess the man in the photograph was a killer.",
            "When Palgrave dies before he can explain the photograph, Miss Marple begins investigating the killing among the resort guests.",
        ]
    )
    api = SimpleNamespace(
        llm_request=SimpleNamespace(
            document_query_intent="summary",
            document_summary_focus="premise",
            attached_document_total_tokens=9000,
            attached_document_capabilities=[
                {
                    "path": file_path,
                    "fits_current_context": False,
                }
            ],
        ),
        _get_active_document_paths=lambda: [file_path],
        _get_active_document_names=lambda: [
            "A Caribbean Mystery - Agatha Christie.epub"
        ],
    )

    result = analyze_loaded_document(
        "explain the premise of this book",
        api=api,
    )

    supporting_evidence = result.split("Supporting evidence:\n\n", 1)[1]
    assert "Golden Palm resort on St. Honore" in supporting_evidence
    assert "snapshot" in supporting_evidence
    assert "investigating the killing among the resort guests" in (
        supporting_evidence
    )
    assert '"Take all this business about Kenya' not in supporting_evidence


@patch("airunner.components.llm.tools.rag_tools.extract_text")
@patch("airunner.components.llm.tools.rag_tools.resolve_existing_file")
def test_analyze_loaded_document_premise_query_prefers_opening_setting(
    mock_resolve,
    mock_extract,
):
    """Premise evidence should keep the opening setting over later side scenes."""
    file_path = "/library/A Caribbean Mystery - Agatha Christie.epub"
    mock_resolve.return_value = file_path
    mock_extract.return_value = "\n\n".join(
        [
            '"TAKE all this business about Kenya," said Major Palgrave. '
            '"Lots of chaps gabbing away who know nothing about the place!"',
            "Old Miss Marple inclined her head while Major Palgrave went on with his travel recollections.",
            "But the pattern was essentially the same as so many elderly bores she had heard before.",
            "It was very gay that evening at the Golden Palm Hotel, where Miss Marple sat at her little corner table and looked out into the warm West Indies night.",
            "Kenya he had talked about Kenya and then India and then for some reason they had got on to murder, and after picking up her ball of wool he began telling her about a snapshot of a murderer.",
            "MOLLY rearranged a few of the table decorations in the dining room, removed an extra knife, straightened a fork, reset a glass or two, and walked out on to the terrace outside.",
            "The subject of murder having come up, he produced his snapshot and asked whether anyone would think the man in the photograph was a killer.",
        ]
    )
    api = SimpleNamespace(
        llm_request=SimpleNamespace(
            document_query_intent="summary",
            document_summary_focus="premise",
            attached_document_total_tokens=9000,
            attached_document_capabilities=[
                {
                    "path": file_path,
                    "fits_current_context": False,
                }
            ],
        ),
        _get_active_document_paths=lambda: [file_path],
        _get_active_document_names=lambda: [
            "A Caribbean Mystery - Agatha Christie.epub"
        ],
    )

    result = analyze_loaded_document(
        "Provide a summary of 'A Caribbean Mystery' including its premise, themes, and key characters.",
        api=api,
    )

    supporting_evidence = result.split("Supporting evidence:\n\n", 1)[1]
    assert "Golden Palm Hotel" in supporting_evidence
    assert "snapshot of a murderer" in supporting_evidence
    assert "MOLLY rearranged" not in supporting_evidence


@patch("airunner.components.llm.tools.rag_tools.extract_text")
@patch("airunner.components.llm.tools.rag_tools.resolve_existing_file")
def test_rag_search_summary_omits_filename_inference_metadata(
    mock_resolve,
    mock_extract,
):
    """Summary evidence should not expose inferred filename bibliography."""
    file_path = (
        "/library/A Graveyard for Lunatics_ Another Tale of - Ray Bradbury.mobi"
    )
    mock_resolve.return_value = file_path
    mock_extract.return_value = (
        "Maximus Films stands beside a cemetery in a surreal Hollywood setting.\n\n"
        "A supposedly dead studio figure appears to return, creating the central mystery."
    )
    api = SimpleNamespace(
        search=Mock(),
        llm_request=_summary_request("premise"),
        _get_active_document_paths=lambda: [file_path],
        _get_active_document_names=lambda: [
            "A Graveyard for Lunatics_ Another Tale of - Ray Bradbury.mobi"
        ],
    )

    result = rag_search("what is this book about?", api=api)

    assert "Current document: loaded document" in result
    assert "Inferred title from filename:" not in result
    assert "Inferred author from filename:" not in result
    assert "Another Tale of" not in result


def test_rag_search_uses_request_rewritten_query_when_available():
    """Document follow-ups should use the preprocess-owned rewritten query."""
    doc = SimpleNamespace(
        metadata={
            "source": "/library/The Satanic Bible - Anton LaVey.pdf",
            "file_name": "The Satanic Bible - Anton LaVey.pdf",
            "file_type": ".pdf",
            "file_path": "/library/The Satanic Bible - Anton LaVey.pdf",
        },
        page_content="Contents page excerpt.",
    )
    search = Mock(return_value=[doc])
    api = SimpleNamespace(
        search=search,
        llm_request=SimpleNamespace(
            rewritten_prompt=(
                "what are the chapters in The Satanic Bible by Anton LaVey?"
            )
        ),
    )

    rag_search("what are the chapters in it?", api=api)

    effective_query = search.call_args.args[0]
    assert effective_query == (
        "what are the chapters in The Satanic Bible by Anton LaVey?"
    )


@patch("airunner.components.llm.tools.rag_tools.extract_text")
@patch("airunner.components.llm.tools.rag_tools.resolve_existing_file")
def test_analyze_loaded_document_returns_full_text_for_small_docs(
    mock_resolve,
    mock_extract,
):
    """Small attached documents should use full-document analysis mode."""
    file_path = "/library/Short Notes.md"
    mock_resolve.return_value = file_path
    mock_extract.return_value = "Short full document text."
    api = SimpleNamespace(
        llm_request=SimpleNamespace(
            attached_document_total_tokens=12,
            attached_document_capabilities=[
                {
                    "path": file_path,
                    "fits_current_context": True,
                }
            ],
        ),
        _get_active_document_paths=lambda: [file_path],
        _get_active_document_names=lambda: ["Short Notes.md"],
    )

    result = analyze_loaded_document("summarize this document", api=api)

    assert "Analysis mode: full_document" in result
    assert "Requested analysis: summarize this document" in result
    assert "Full document text:" in result
    assert "Short full document text." in result


@patch("airunner.components.llm.tools.rag_tools.extract_text")
@patch("airunner.components.llm.tools.rag_tools.resolve_existing_file")
def test_analyze_loaded_document_returns_chunked_context_for_large_docs(
    mock_resolve,
    mock_extract,
):
    """Large attached documents should use chunked analysis mode."""
    file_path = "/library/The Satanic Bible - Anton LaVey.pdf"
    mock_resolve.return_value = file_path
    mock_extract.return_value = (
        "INTRODUCTION\n\n"
        "The introduction frames Satanism as a realism-first philosophy.\n\n"
        "THE BOOK OF SATAN\n\n"
        "This section rejects Christian mysticism and centers the real world.\n\n"
        "THE BOOK OF LUCIFER\n\n"
        "This section presents key arguments and practical philosophy.\n\n"
        "THE BOOK OF BELIAL\n\n"
        "This section focuses on ritual as applied practice.\n\n"
        "THE BOOK OF LEVIATHAN\n\n"
        "This section contains later material and ceremonial text."
    )
    api = SimpleNamespace(
        llm_request=SimpleNamespace(
            document_query_intent="summary",
            document_summary_focus="premise",
            attached_document_total_tokens=9000,
            attached_document_capabilities=[
                {
                    "path": file_path,
                    "fits_current_context": False,
                }
            ],
        ),
        _get_active_document_paths=lambda: [file_path],
        _get_active_document_names=lambda: [
            "The Satanic Bible - Anton LaVey.pdf"
        ],
    )

    result = analyze_loaded_document("summarize this document", api=api)

    assert "Analysis mode: chunked_document" in result
    assert "Analysis pipeline: distributed_evidence_bundle" in result
    assert "Document coverage:" in result
    assert "Refined whole-document synthesis:" in result
    assert "Overview:" in result
    assert "Chunk summaries:" in result
    assert "Supporting evidence:" in result
    assert "[Excerpt 1]" in result
    assert "1. INTRODUCTION" in result
    assert "2. THE BOOK OF SATAN" in result
    assert "Section: THE BOOK OF SATAN." in result


@patch("airunner.components.llm.tools.rag_tools.extract_text")
@patch("airunner.components.llm.tools.rag_tools.resolve_existing_file")
def test_analyze_loaded_document_uses_generic_chapter_headings(
    mock_resolve,
    mock_extract,
):
    """Novel-style all-caps chapter headings should drive chunked analysis."""
    file_path = "/library/A Caribbean Mystery - Agatha Christie.epub"
    mock_resolve.return_value = file_path
    mock_extract.return_value = (
        "MAJOR PALGRAVE TELLS A STORY\n\n"
        "Miss Marple listens to Major Palgrave at a Caribbean resort while he circles toward a murder anecdote.\n\n"
        "He produces a snapshot that may identify a killer.\n\n"
        "A DEATH IN THE HOTEL\n\n"
        "Palgrave dies before he can explain the photograph.\n\n"
        "Miss Marple begins piecing together what he meant and who is at risk."
    )
    api = SimpleNamespace(
        llm_request=SimpleNamespace(
            document_query_intent="summary",
            document_summary_focus="premise",
            attached_document_total_tokens=9000,
            attached_document_capabilities=[
                {
                    "path": file_path,
                    "fits_current_context": False,
                }
            ],
        ),
        _get_active_document_paths=lambda: [file_path],
        _get_active_document_names=lambda: [
            "A Caribbean Mystery - Agatha Christie.epub"
        ],
    )

    result = analyze_loaded_document("summarize this document", api=api)

    assert "Analysis mode: chunked_document" in result
    assert "Document coverage:" in result
    assert "1. MAJOR PALGRAVE TELLS A STORY" in result
    assert "2. A DEATH IN THE HOTEL" in result


@patch("airunner.components.llm.tools.rag_tools.extract_text")
@patch("airunner.components.llm.tools.rag_tools.resolve_existing_file")
def test_analyze_loaded_document_premise_query_frontloads_early_chapters(
    mock_resolve,
    mock_extract,
):
    """Premise summaries should keep early chapters instead of late samples."""
    file_path = "/library/A Caribbean Mystery - Agatha Christie.epub"
    mock_resolve.return_value = file_path
    mock_extract.return_value = (
        "A Caribbean Mystery\n\n"
        "Agatha Christie\n\n"
        "MAJOR PALGRAVE TELLS A STORY\n\n"
        "Miss Marple listens to Major Palgrave at a Caribbean resort while he turns toward a murder anecdote.\n\n"
        "A DEATH IN THE HOTEL\n\n"
        "Palgrave dies before he can explain the photograph and the mystery becomes urgent.\n\n"
        "MISS MARPLE SEEKS MEDICAL ATTENTION\n\n"
        "Miss Marple talks to Dr. Graham while quietly piecing together what the missing snapshot means.\n\n"
        "MISS MARPLE MAKES A DECISION\n\n"
        "She decides she cannot ignore the danger around the hotel guests.\n\n"
        "IN THE SMALL HOURS\n\n"
        "During the night she replays the clues and the people connected to Palgrave.\n\n"
        "MORNING ON THE BEACH\n\n"
        "Fresh conversations sharpen her view of the relationships at the resort.\n\n"
        "A TALK WITH ESTHER WALTERS\n\n"
        "Later witness interviews add detail about side suspicions and private tensions.\n\n"
        "EXIT VICTORIA JOHNSON\n\n"
        "A much later chapter shifts toward consequences after the core setup is already clear."
    )
    api = SimpleNamespace(
        llm_request=SimpleNamespace(
            document_query_intent="summary",
            document_summary_focus="premise",
            attached_document_total_tokens=9000,
            attached_document_capabilities=[
                {
                    "path": file_path,
                    "fits_current_context": False,
                }
            ],
        ),
        _get_active_document_paths=lambda: [file_path],
        _get_active_document_names=lambda: [
            "A Caribbean Mystery - Agatha Christie.epub"
        ],
    )

    result = analyze_loaded_document("what is this book about?", api=api)

    assert "Document coverage:" in result
    assert "1. MAJOR PALGRAVE TELLS A STORY" in result
    assert "2. A DEATH IN THE HOTEL" in result
    assert "3. MISS MARPLE SEEKS MEDICAL ATTENTION" in result
    assert "6. MORNING ON THE BEACH" in result
    assert "A TALK WITH ESTHER WALTERS" not in result
    assert "EXIT VICTORIA JOHNSON" not in result


@patch("airunner.components.llm.tools.rag_tools.extract_text")
@patch("airunner.components.llm.tools.rag_tools.resolve_existing_file")
def test_inspect_loaded_documents_returns_structure_for_single_active_doc(
    mock_resolve,
    mock_extract,
):
    """Inspection should expose active document metadata and structure."""
    file_path = "/library/The Satanic Bible - Anton LaVey.pdf"
    mock_resolve.return_value = file_path
    mock_extract.return_value = (
        "INTRODUCTION\n\nPROLOGUE\n\nTHE BOOK OF SATAN\n\n"
        "THE BOOK OF LUCIFER\n\nTHE BOOK OF BELIAL\n\n"
        "THE BOOK OF LEVIATHAN"
    )
    api = SimpleNamespace(
        _get_active_document_paths=lambda: [file_path],
        _get_active_document_names=lambda: [
            "The Satanic Bible - Anton LaVey.pdf"
        ],
    )

    result = inspect_loaded_documents(api=api)

    assert "Loaded documents:" in result
    assert "Document structure:" in result
    assert "Inferred title from filename: The Satanic Bible" in result
    assert "1. INTRODUCTION" in result
    assert "3. THE BOOK OF SATAN" in result
    assert "6. THE BOOK OF LEVIATHAN" in result


@patch("airunner.components.llm.tools.rag_tools.extract_text")
@patch("airunner.components.llm.tools.rag_tools.resolve_existing_file")
def test_inspect_loaded_documents_returns_metadata_without_structure(
    mock_resolve,
    mock_extract,
):
    """Inspection should still return metadata when no headings exist."""
    file_path = "/library/The Satanic Bible - Anton LaVey.pdf"
    mock_resolve.return_value = file_path
    mock_extract.return_value = "Ordinary prose without heading markers."
    api = SimpleNamespace(
        _get_active_document_paths=lambda: [file_path],
        _get_active_document_names=lambda: [
            "The Satanic Bible - Anton LaVey.pdf"
        ],
    )

    result = inspect_loaded_documents(api=api)

    assert "Loaded documents:" in result
    assert "Document structure:" not in result
    assert (
        "Stored path: /library/The Satanic Bible - Anton LaVey.pdf"
        in result
    )


@patch("airunner.components.llm.tools.rag_tools.PathSettings.objects.first")
def test_save_to_knowledge_base_errors_without_path_settings(mock_first):
    """Saving KB content should fail clearly without a configured base path."""
    mock_first.return_value = None

    result = save_to_knowledge_base(
        "content",
        "Example",
        api=None,
    )

    assert "No knowledge base path is configured" in result


@patch("airunner.components.llm.tools.rag_tools.Document")
@patch("airunner.components.llm.tools.rag_tools.os.walk")
@patch("airunner.components.llm.tools.rag_tools.os.path.exists")
@patch("airunner.components.llm.tools.rag_tools.session_scope")
def test_search_knowledge_base_documents_discovers_files_from_settings(
    mock_session_scope,
    mock_exists,
    mock_walk,
    mock_document,
):
    """KB search should discover supported files from configured paths."""
    discovered_path = "/library/documents/python_notes.txt"
    doc = SimpleNamespace(path=discovered_path, indexed=False)
    session = _build_session_with_active_docs([], [doc])
    mock_session_scope.return_value.__enter__.return_value = session
    mock_exists.side_effect = (
        lambda path: path == "/library/documents"
    )
    mock_walk.return_value = [
        ("/library/documents", [], ["python_notes.txt", "ignore.bin"])
    ]
    mock_document.objects.filter_by.return_value = []

    api = SimpleNamespace(
        path_settings=SimpleNamespace(
            documents_path="/library/documents",
            ebook_path="/library/ebooks",
            webpages_path="/library/webpages",
            base_path="/library",
        ),
        emit_signal=Mock(),
    )

    result = search_knowledge_base_documents("python", api=api)

    mock_document.objects.create.assert_called_once_with(
        path=discovered_path,
        active=True,
        indexed=False,
    )
    api.emit_signal.assert_called_once()
    assert "Found 1 relevant document(s) for 'python'" in result
    assert "python_notes.txt (not indexed)" in result
    assert discovered_path in result


@patch("airunner.components.llm.tools.rag_tools.PathSettings.objects.first")
@patch("airunner.components.llm.tools.rag_tools.Document")
@patch("airunner.components.llm.tools.rag_tools.os.walk")
@patch("airunner.components.llm.tools.rag_tools.os.path.exists")
@patch("airunner.components.llm.tools.rag_tools.session_scope")
def test_search_knowledge_base_documents_uses_repo_fallback_discovery(
    mock_session_scope,
    mock_exists,
    mock_walk,
    mock_document,
    mock_first,
):
    """KB search should fall back to bundled repo sample documents."""
    from airunner.components.llm.tools import rag_tools as rag_tools_module

    repo_root = os.path.abspath(
        os.path.join(
            os.path.dirname(rag_tools_module.__file__),
            "..",
            "..",
            "..",
            "..",
            "..",
        )
    )
    fallback_dir = os.path.join(
        repo_root,
        "booksite",
        "text",
        "other",
        "documents",
    )
    discovered_path = os.path.join(fallback_dir, "mystery.epub")
    doc = SimpleNamespace(path=discovered_path, indexed=False)
    session = _build_session_with_active_docs([], [], [doc])
    mock_session_scope.return_value.__enter__.return_value = session
    mock_first.return_value = None

    def exists_side_effect(path: str) -> bool:
        return path in {
            os.path.join(repo_root, "booksite"),
            fallback_dir,
        }

    mock_exists.side_effect = exists_side_effect
    mock_walk.return_value = [(fallback_dir, [], ["mystery.epub"])]
    mock_document.objects.filter_by.return_value = []

    api = SimpleNamespace(emit_signal=Mock())

    result = search_knowledge_base_documents("mystery", api=api)

    mock_document.objects.create.assert_called_once_with(
        path=discovered_path,
        active=True,
        indexed=False,
    )
    api.emit_signal.assert_called_once()
    assert "mystery.epub (not indexed)" in result
    assert discovered_path in result


@patch("airunner.components.llm.tools.rag_tools.session_scope")
def test_search_knowledge_base_documents_indexes_matched_results(
    mock_session_scope,
):
    """KB search should index matched files before formatting output."""
    doc = SimpleNamespace(path="/library/python-guide.pdf", indexed=False)
    session = _build_session_with_active_docs([doc])
    mock_session_scope.return_value.__enter__.return_value = session
    rag_manager = SimpleNamespace(ensure_indexed_files=Mock(return_value=True))
    api = SimpleNamespace(rag_manager=rag_manager)

    result = search_knowledge_base_documents("python", api=api)

    rag_manager.ensure_indexed_files.assert_called_once_with(
        ["/library/python-guide.pdf"]
    )
    assert "Automatically indexed 1 document(s)" in result
    assert "python-guide.pdf (indexed)" in result


@patch("airunner.components.llm.tools.rag_tools.os.path.exists")
@patch("airunner.components.llm.tools.rag_tools.session_scope")
def test_search_knowledge_base_documents_handles_empty_knowledge_base(
    mock_session_scope,
    mock_exists,
):
    """KB search should return a clear message when no docs exist."""
    session = _build_session_with_active_docs([])
    mock_session_scope.return_value.__enter__.return_value = session
    mock_exists.return_value = False

    result = search_knowledge_base_documents("python")

    assert "No documents found in knowledge base" in result
