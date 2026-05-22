"""Unit tests for RAG tool result formatting."""

from types import SimpleNamespace
from unittest.mock import Mock, patch

from airunner.components.llm.tools.rag_tools import (
    inspect_loaded_documents,
    rag_search,
    save_to_knowledge_base,
)


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


def test_rag_search_uses_standard_retrieval_breadth():
    """Summary fallback retrieval should request a wider result set."""
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


def test_rag_search_expands_single_document_pronoun_queries():
    """Single-document follow-ups should include the active doc name."""
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
        _get_active_document_names=lambda: [
            "The Satanic Bible - Anton LaVey.pdf"
        ],
    )

    rag_search("what are the chapters in it?", api=api)

    effective_query = search.call_args.args[0]
    assert "what are the chapters in it?" in effective_query
    assert "The Satanic Bible" in effective_query
    assert "Anton LaVey" in effective_query


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
