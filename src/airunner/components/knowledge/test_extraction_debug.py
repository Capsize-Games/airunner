"""
Test knowledge extraction directly to diagnose the issue.
"""

from airunner.components.knowledge.user_knowledge_manager import (
    UserKnowledgeManager,
)


def mock_llm_extraction(prompt, **kwargs):
    """Mock LLM that returns valid JSON for testing."""
    if "correction" in prompt.lower():
        # Mock correction detection - no corrections
        return "[]"
    else:
        # Mock fact extraction
        return """[
            {"text": "User is experiencing back pain", "category": "health", "confidence": 0.95},
            {"text": "User has neck pain", "category": "health", "confidence": 0.90},
            {"text": "User's pain is in upper left shoulder", "category": "health", "confidence": 0.85}
        ]"""


def test_extraction():
    print("=" * 70)
    print("Testing Knowledge Extraction Directly")
    print("=" * 70)
    print()

    # Clear existing facts
    manager = UserKnowledgeManager()
    manager.clear_facts()

    # Test WITHOUT correction detection first
    print("Step 1: Testing _parse_facts_from_response...")
    test_response = """[
        {"text": "User is experiencing back pain", "category": "health", "confidence": 0.95}
    ]"""
    try:
        facts = manager._parse_facts_from_response(test_response)
        print(f"✅ Parsed {len(facts)} facts directly")
        for fact in facts:
            print(f"   - [{fact.category.value}] {fact.text}")
    except Exception as e:
        print(f"❌ Parsing failed: {e}")
        import traceback

        traceback.print_exc()
    print()

    # Test extraction (which includes correction detection)
    print("Step 2: Testing full extraction...")
    user_message = "my neck and back are killing me"
    bot_response = "I'm sorry to hear that"

    print(f"User: {user_message}")
    print(f"Bot: {bot_response}")
    print()

    print("Extracting facts...")
    try:
        facts = manager.extract_facts_from_text(
            user_message, bot_response, mock_llm_extraction
        )

        print(f"✅ Extracted {len(facts)} facts:")
        for fact in facts:
            print(
                f"   - [{fact.category.value}] {fact.text} ({int(fact.confidence*100)}%)"
            )
        print()

        # Add facts to manager
        if facts:
            manager.add_facts(facts)
            print(f"✅ Added {len(facts)} facts to knowledge base")
            print()

        # Verify facts were saved
        print("Verifying persistence...")
        manager2 = UserKnowledgeManager()
        loaded_facts = manager2.get_all_facts()
        print(f"✅ Loaded {len(loaded_facts)} facts from disk:")
        for fact in loaded_facts:
            print(f"   - [{fact.category.value}] {fact.text}")
        print()

        # Test context generation
        print("Testing context generation...")
        context = manager2.get_context_for_conversation(
            core_facts_count=10,
            rag_facts_count=5,
            use_rag=True,
            query="my back hurts",
        )
        print(f"Context:\n{context}")

        if not context:
            print("❌ WARNING: Context is empty!")

    except Exception as e:
        print(f"❌ Error during extraction: {e}")
        import traceback

        traceback.print_exc()

    print()
    print("=" * 70)
    print("Extraction test complete")
    print("=" * 70)


if __name__ == "__main__":
    test_extraction()
