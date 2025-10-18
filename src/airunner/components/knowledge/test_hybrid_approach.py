"""
Test the hybrid approach: core facts + RAG retrieval.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from airunner.components.knowledge.user_knowledge_manager import (
    UserKnowledgeManager,
)
from airunner.components.knowledge.data import Fact, FactCategory


def test_hybrid_approach():
    """Test core facts vs RAG retrieval."""
    print("=" * 70)
    print("Testing Hybrid Approach: Core Facts + RAG Retrieval")
    print("=" * 70)

    km = UserKnowledgeManager()

    print(f"\n📊 Total facts in knowledge base: {len(km.facts_cache)}")

    # Test 1: Core facts (always injected)
    print("\n" + "=" * 70)
    print("Test 1: Core Facts (Always Injected)")
    print("=" * 70)
    print("Categories: identity, location, preferences")

    core_facts = km.get_core_facts(max_facts=10)
    print(f"\n✅ Retrieved {len(core_facts)} core facts:")
    for fact in core_facts:
        print(f"   - [{fact.category.value}] {fact.text}")

    # Test 2: RAG retrieval for health query
    print("\n" + "=" * 70)
    print("Test 2: RAG Retrieval for Health Query")
    print("=" * 70)
    print("Query: 'tell me about my health issues'")

    health_query = "tell me about my health issues"
    rag_facts = km.get_relevant_facts(query=health_query, max_facts=5)
    print(f"\n✅ Retrieved {len(rag_facts)} relevant facts:")
    for fact in rag_facts:
        print(f"   - [{fact.category.value}] {fact.text}")

    # Test 3: RAG retrieval for work query
    print("\n" + "=" * 70)
    print("Test 3: RAG Retrieval for Work Query")
    print("=" * 70)
    print("Query: 'what do i do for work?'")

    work_query = "what do i do for work?"
    work_facts = km.get_relevant_facts(query=work_query, max_facts=5)
    print(f"\n✅ Retrieved {len(work_facts)} relevant facts:")
    for fact in work_facts:
        print(f"   - [{fact.category.value}] {fact.text}")

    # Test 4: Hybrid context (core + RAG)
    print("\n" + "=" * 70)
    print("Test 4: Hybrid Context (Core + RAG)")
    print("=" * 70)
    print("Core: 5 facts | RAG: 3 facts | Query: 'my back hurts'")

    hybrid_context = km.get_context_for_conversation(
        query="my back hurts",
        core_facts_count=5,
        rag_facts_count=3,
        use_rag=True,
    )
    print(f"\n✅ Hybrid context generated:")
    print(hybrid_context)

    # Test 5: Legacy mode (backward compatibility)
    print("\n" + "=" * 70)
    print("Test 5: Legacy Mode (Backward Compatible)")
    print("=" * 70)
    print("Top 10 facts by confidence (no RAG)")

    legacy_context = km.get_context_for_conversation(max_facts=10)
    print(f"\n✅ Legacy context generated:")
    print(legacy_context)

    # Token comparison
    print("\n" + "=" * 70)
    print("Token Comparison")
    print("=" * 70)

    hybrid_tokens = len(hybrid_context.split())
    legacy_tokens = len(legacy_context.split())

    print(f"Hybrid approach (5 core + 3 RAG): ~{hybrid_tokens} tokens")
    print(f"Legacy approach (top 10): ~{legacy_tokens} tokens")
    print(
        f"Savings: ~{legacy_tokens - hybrid_tokens} tokens "
        f"({((legacy_tokens - hybrid_tokens) / legacy_tokens * 100):.1f}%)"
    )

    print("\n" + "=" * 70)
    print("✅ All tests complete!")
    print("=" * 70)


if __name__ == "__main__":
    test_hybrid_approach()
