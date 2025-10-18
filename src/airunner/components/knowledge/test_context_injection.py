"""
Test that user knowledge is properly injected into system prompts.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from airunner.components.knowledge.user_knowledge_manager import (
    UserKnowledgeManager,
)


def test_context_injection():
    """Test that get_context_for_conversation formats facts correctly."""
    print("=" * 60)
    print("Testing Context Injection")
    print("=" * 60)

    km = UserKnowledgeManager()

    # Get formatted context
    context = km.get_context_for_conversation(max_facts=20)

    print("\n📝 Current facts in knowledge base:")
    print(f"Total facts: {len(km.facts_cache)}")

    print("\n📄 Formatted context for system prompt:")
    print(context)

    if context:
        print("\n✅ Context generated successfully!")
        print(f"   - Contains {len(context.split(chr(10)))} lines")
        print(f"   - {len(context)} characters total")

        # Verify format
        assert "## What I know about you:" in context, "Missing header"
        assert context.count("- ") == len(
            km.facts_cache
        ), "Missing fact bullets"
        assert (
            "do not repeat questions or advice the user has already addressed"
            in context.lower()
        ), "Missing repetition guard instructions"

        print("\n✅ All format checks passed!")
    else:
        print("\n⚠️  No context generated (knowledge base is empty)")

    print("\n" + "=" * 60)
    print("ℹ️  This context will be automatically injected into")
    print("   the system prompt for every conversation!")
    print("=" * 60)


if __name__ == "__main__":
    test_context_injection()
