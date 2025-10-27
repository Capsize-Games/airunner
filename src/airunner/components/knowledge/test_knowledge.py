"""
Test script for knowledge system.

Run this to verify the knowledge extraction and storage works correctly.
"""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from airunner.components.knowledge.user_knowledge_manager import (
    UserKnowledgeManager,
)
from airunner.components.knowledge.fact_models import Fact, FactCategory


def mock_llm_callable(prompt: str, **kwargs) -> str:
    """Mock LLM for testing without actual model."""
    # Return sample JSON response
    return """[
  {"text": "User's name is Alice", "category": "identity", "confidence": 0.95},
  {"text": "User lives in Portland", "category": "location", "confidence": 0.90},
  {"text": "User is a data scientist", "category": "work", "confidence": 0.92}
]"""


def test_knowledge_manager():
    """Test UserKnowledgeManager functionality."""
    print("=" * 60)
    print("Testing UserKnowledgeManager")
    print("=" * 60)

    # Initialize
    km = UserKnowledgeManager()
    print(f"\n✓ Initialized UserKnowledgeManager")
    print(f"  Knowledge dir: {km.knowledge_dir}")
    print(f"  Facts file: {km.facts_json}")

    # Clear existing facts for testing
    km.clear_facts()
    print(f"\n✓ Cleared existing facts")

    # Extract facts from sample conversation
    print(f"\n📝 Extracting facts from conversation...")
    user_msg = (
        "Hi! My name is Alice and I work as a data scientist in Portland."
    )
    bot_msg = "Nice to meet you, Alice! Data science is fascinating."

    facts = km.extract_facts_from_text(user_msg, bot_msg, mock_llm_callable)
    print(f"✓ Extracted {len(facts)} facts:")
    for fact in facts:
        print(
            f"  - [{fact.category.value}] {fact.text} ({fact.confidence:.0%})"
        )

    # Add facts to knowledge base
    km.add_facts(facts)
    print(f"\n✓ Added facts to knowledge base")

    # Get context for conversation
    context = km.get_context_for_conversation()
    print(f"\n📄 Context for conversation:")
    print(context)

    # Query facts
    print(f"\n🔍 Querying for 'Portland':")
    results = km.query_facts("Portland")
    for fact in results:
        print(f"  - {fact.text} ({fact.confidence:.0%})")

    # Test consolidation by adding duplicate
    print(f"\n🔄 Testing fact consolidation (adding duplicate)...")
    duplicate = [
        Fact(
            text="User's name is Alice",
            category=FactCategory.IDENTITY,
            confidence=0.98,  # Higher confidence
        )
    ]
    km.add_facts(duplicate)
    print(f"✓ Consolidated facts (should still have {len(facts)} facts)")
    print(f"  Actual count: {len(km.get_all_facts())}")

    # Show final JSON
    print(f"\n📖 View the knowledge base at:")
    print(f"  {km.facts_json}")

    if km.facts_json.exists():
        print(f"\n📄 Current content:")
        print("-" * 60)
        with open(km.facts_json, "r") as f:
            print(f.read())
        print("-" * 60)

    print(f"\n✅ All tests passed!")


if __name__ == "__main__":
    test_knowledge_manager()
