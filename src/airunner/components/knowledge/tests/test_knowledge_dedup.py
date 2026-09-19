"""Desktop-side regression test for KnowledgeBase entity-overlap dedup.

The desktop copy of ``_is_duplicate_fact`` had the same entity-extraction
bug as the services copy: it read entities from a stale loop variable (the
last line of the section for every comparison), so the >80% entity-overlap
strategy was effectively inert. Both copies now pair each normalized fact
with its own raw line before extracting entities.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from airunner.components.knowledge.knowledge_base import (
    KnowledgeBase,
    _extract_entities,
)


@pytest.fixture()
def kb(tmp_path: Path) -> KnowledgeBase:
    """A knowledge base backed by an isolated temporary directory."""
    return KnowledgeBase(knowledge_dir=tmp_path)


def test_extract_entities_uses_original_casing() -> None:
    assert _extract_entities(
        "Alice Johnson manages the Phoenix Project"
    ) == {"Alice Johnson", "Phoenix Project"}
    assert _extract_entities(
        "alice johnson manages the phoenix project"
    ) == set()


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
