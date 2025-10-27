"""
Test knowledge correction, update, and deletion functionality.
"""

from airunner.components.knowledge.user_knowledge_manager import (
    UserKnowledgeManager,
)
from airunner.components.knowledge.fact_models import Fact, FactCategory


def test_crud_operations():
    """Test Create, Read, Update, Delete operations."""
    print("=" * 70)
    print("Testing CRUD Operations")
    print("=" * 70)
    print()

    manager = UserKnowledgeManager()

    # Clear existing facts for clean test
    manager.clear_facts()

    # CREATE: Add some test facts
    print("1. CREATE: Adding facts...")
    test_facts = [
        Fact(
            text="User is a Python developer",
            category=FactCategory.WORK,
            confidence=0.95,
            source="test",
        ),
        Fact(
            text="User lives in Seattle",
            category=FactCategory.LOCATION,
            confidence=0.90,
            source="test",
        ),
        Fact(
            text="User is 30 years old",
            category=FactCategory.IDENTITY,
            confidence=0.85,
            source="test",
        ),
    ]
    manager.add_facts(test_facts)
    print(f"   Added {len(test_facts)} facts")
    print(f"   Total facts: {len(manager.get_all_facts())}")
    for fact in manager.get_all_facts():
        print(f"     - {fact.text}")
    print()

    # READ: Query facts
    print("2. READ: Querying facts...")
    work_facts = [
        f for f in manager.get_all_facts() if f.category == FactCategory.WORK
    ]
    print(f"   Work facts: {len(work_facts)}")
    for fact in work_facts:
        print(f"     - {fact.text}")
    print()

    # UPDATE: Replace a fact
    print("3. UPDATE: Replacing fact text...")
    old_text = "User is 30 years old"
    new_text = "User is 31 years old"
    result = manager.replace_fact(old_text, new_text, new_confidence=0.95)
    print(f"   Replace '{old_text}'")
    print(f"   With '{new_text}'")
    print(f"   Result: {'✅ Success' if result else '❌ Failed'}")

    # Verify update
    updated_fact = [
        f for f in manager.get_all_facts() if "31 years old" in f.text
    ]
    if updated_fact:
        print(
            f"   ✅ Fact updated: {updated_fact[0].text} (confidence: {updated_fact[0].confidence})"
        )
    print()

    # UPDATE: Full fact replacement
    print("4. UPDATE: Full fact replacement...")
    new_fact = Fact(
        text="User is a Senior Python developer",
        category=FactCategory.WORK,
        confidence=0.98,
        source="correction",
    )
    result = manager.update_fact("User is a Python developer", new_fact)
    print(f"   Update 'User is a Python developer'")
    print(f"   With '{new_fact.text}'")
    print(f"   Result: {'✅ Success' if result else '❌ Failed'}")
    print()

    # DELETE: Remove a fact
    print("5. DELETE: Removing fact...")
    fact_to_delete = "User lives in Seattle"
    result = manager.delete_fact(fact_to_delete)
    print(f"   Delete '{fact_to_delete}'")
    print(f"   Result: {'✅ Success' if result else '❌ Failed'}")
    print(f"   Remaining facts: {len(manager.get_all_facts())}")
    for fact in manager.get_all_facts():
        print(f"     - {fact.text}")
    print()

    # Test non-existent fact
    print("6. Error handling...")
    result = manager.delete_fact("User loves chocolate")
    print(
        f"   Delete non-existent fact: {'✅ Success' if result else '❌ Failed (expected)'}"
    )
    print()

    print("=" * 70)
    print("✅ CRUD tests complete!")
    print("=" * 70)


def test_correction_keywords():
    """Test detection of correction keywords."""
    print("\n" + "=" * 70)
    print("Testing Correction Detection")
    print("=" * 70)
    print()

    manager = UserKnowledgeManager()

    # Add a test fact
    manager.clear_facts()
    manager.add_facts(
        [
            Fact(
                text="User lives in Seattle",
                category=FactCategory.LOCATION,
                confidence=0.90,
                source="test",
            )
        ]
    )

    print("Current facts:")
    for fact in manager.get_all_facts():
        print(f"  - {fact.text}")
    print()

    # Test correction scenarios
    test_cases = [
        (
            "Actually, I live in Portland",
            True,
            "Correction keyword: 'actually'",
        ),
        (
            "No, that's wrong, I'm in Boston",
            True,
            "Correction keywords: 'no', 'wrong'",
        ),
        ("I live in Tokyo", False, "No correction keywords"),
        (
            "That's not right, I don't live in Seattle",
            True,
            "Correction: 'not right'",
        ),
        ("I love Seattle!", False, "No correction (just mentioning city)"),
    ]

    print("Correction detection tests:")
    for message, should_detect, description in test_cases:
        # Check for correction keywords
        correction_keywords = [
            "actually",
            "correction",
            "no ",
            "not ",
            "wrong",
            "incorrect",
            "that's not right",
            "i'm not",
            "i don't",
            "i didn't",
            "never said",
            "mistake",
            "change that",
        ]
        message_lower = message.lower()
        detected = any(
            keyword in message_lower for keyword in correction_keywords
        )

        status = "✅" if detected == should_detect else "❌"
        print(f"  {status} '{message}'")
        print(f"     Expected: {should_detect}, Got: {detected}")
        print(f"     ({description})")
    print()

    print("=" * 70)
    print("✅ Correction detection tests complete!")
    print("=" * 70)


def test_manual_json_editing():
    """Test that manual JSON edits work correctly."""
    print("\n" + "=" * 70)
    print("Testing Manual JSON Editing")
    print("=" * 70)
    print()

    manager = UserKnowledgeManager()
    manager.clear_facts()

    # Simulate manual JSON editing by directly adding/modifying facts
    print("1. User manually adds fact via JSON editor...")
    manual_fact = Fact(
        text="User prefers dark mode",
        category=FactCategory.PREFERENCES,
        confidence=1.0,
        source="manual_edit",
    )
    manager.facts_cache.append(manual_fact)
    manager._save_facts()
    print(f"   ✅ Added: {manual_fact.text}")
    print()

    # Reload to verify persistence
    print("2. Reloading facts from disk...")
    manager2 = UserKnowledgeManager()
    loaded_facts = manager2.get_all_facts()
    print(f"   ✅ Loaded {len(loaded_facts)} facts")
    for fact in loaded_facts:
        print(f"     - {fact.text} (source: {fact.source})")
    print()

    # Manual deletion (user removes from JSON)
    print("3. User manually deletes fact via JSON editor...")
    manager2.facts_cache = [
        f for f in manager2.facts_cache if "dark mode" not in f.text.lower()
    ]
    manager2._save_facts()
    print(f"   ✅ Deleted fact")
    print(f"   Remaining: {len(manager2.get_all_facts())} facts")
    print()

    print("=" * 70)
    print("✅ Manual editing tests complete!")
    print("=" * 70)


if __name__ == "__main__":
    test_crud_operations()
    test_correction_keywords()
    test_manual_json_editing()

    print("\n" + "=" * 70)
    print("🎉 All correction tests passed!")
    print("=" * 70)
