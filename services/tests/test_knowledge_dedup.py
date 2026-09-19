"""Regression tests for KnowledgeBase fact deduplication.

``_is_duplicate_fact``'s third strategy is entity overlap: two facts with
>80% entity overlap and >70% word overlap count as duplicates. Entity
extraction only matches capitalized words, but the normalized (lowercased)
fact was being fed to it, so the entity set was always empty and that
strategy could never fire. The desktop copy of the class had the same bug
via a stale loop variable. Both now pair each normalized fact with its raw
line before extracting entities.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from airunner_services.knowledge import KnowledgeBase, _extract_entities


@pytest.fixture()
def kb(tmp_path: Path) -> KnowledgeBase:
    """A knowledge base backed by an isolated temporary directory."""
    return KnowledgeBase(knowledge_dir=tmp_path)


def test_extract_entities_requires_original_casing() -> None:
    """Entities come from capitalized text; normalization destroys them."""
    assert _extract_entities(
        "Alice Johnson manages the Phoenix Project"
    ) == {"Alice Johnson", "Phoenix Project"}
    assert _extract_entities(
        "alice johnson manages the phoenix project"
    ) == set()


def test_exact_duplicate_is_rejected(kb: KnowledgeBase) -> None:
    assert kb.add_fact("Alice prefers tea", section="Notes") is True
    assert kb.add_fact("Alice prefers tea", section="Notes") is False


def test_entity_overlap_duplicate_is_rejected(kb: KnowledgeBase) -> None:
    """A near-exact paraphrase is caught by the entity-overlap strategy."""
    assert (
        kb.add_fact(
            "Alice Johnson manages the Phoenix Project", section="Notes"
        )
        is True
    )
    assert (
        kb.add_fact(
            "Alice Johnson manages the Phoenix Project team", section="Notes"
        )
        is False
    )


def test_distinct_fact_is_accepted(kb: KnowledgeBase) -> None:
    assert (
        kb.add_fact(
            "Alice Johnson manages the Phoenix Project", section="Notes"
        )
        is True
    )
    assert (
        kb.add_fact("Bob Smith prefers tea over coffee", section="Notes")
        is True
    )
