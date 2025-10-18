"""
Test script for conversation analysis system.

Run this to verify analyzers work correctly.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from airunner.components.llm.managers.agent.analysis import (
    AnalysisManager,
    MoodAnalyzer,
    SentimentAnalyzer,
    RelationshipAnalyzer,
)


def mock_llm_callable(prompt: str, **kwargs) -> str:
    """Mock LLM for testing."""
    print(f"\n📤 LLM Call ({kwargs.get('max_tokens', 200)} tokens max)")
    print(f"   Temperature: {kwargs.get('temperature', 0.3)}")
    print(f"   Prompt length: {len(prompt)} chars")
    print(f"   Prompt preview: {prompt[:200]}...")

    # Detect analyzer type from prompt
    if "emotional state" in prompt.lower() and "valence" in prompt.lower():
        # Mood analyzer
        return """{
  "primary_emotion": "empathetic",
  "intensity": 0.7,
  "valence": 0.6,
  "arousal": 0.5,
  "dominance": 0.6,
  "engagement": 0.8,
  "rapport": 0.7,
  "emoji": "😊",
  "description": "Feeling caring and supportive after user shared their pain"
}"""

    elif "user's emotional state" in prompt.lower():
        # Sentiment analyzer
        return """{
  "sentiment": "negative",
  "emotions": ["frustration", "pain", "discomfort"],
  "intensity": 0.8,
  "user_needs": ["help", "validation", "reassurance"],
  "tone": "urgent"
}"""

    elif "relationship" in prompt.lower():
        # Relationship analyzer
        return """{
  "level": "acquaintance",
  "trust": 0.6,
  "openness": 0.7,
  "mutual_understanding": 0.5,
  "shared_experiences": 2,
  "comfort_level": 0.6,
  "formality": 0.5
}"""

    return "{}"


def test_individual_analyzers():
    """Test each analyzer separately."""
    print("=" * 70)
    print("Testing Individual Analyzers")
    print("=" * 70)

    user_msg = "my neck and back are killing me. tons of pain"
    bot_msg = (
        "I'm sorry to hear that. Have you tried any specific exercises or "
        "stretches to alleviate the pain?"
    )

    # Test MoodAnalyzer
    print("\n1️⃣  Testing MoodAnalyzer...")
    mood_analyzer = MoodAnalyzer()
    result = mood_analyzer.analyze(
        user_msg, bot_msg, mock_llm_callable, conversation_history=[]
    )
    print(f"✅ Success: {result.success}")
    print(f"📊 Data: {result.data}")

    # Test SentimentAnalyzer
    print("\n2️⃣  Testing SentimentAnalyzer...")
    sentiment_analyzer = SentimentAnalyzer()
    result = sentiment_analyzer.analyze(
        user_msg, bot_msg, mock_llm_callable, conversation_history=[]
    )
    print(f"✅ Success: {result.success}")
    print(f"📊 Data: {result.data}")

    # Test RelationshipAnalyzer
    print("\n3️⃣  Testing RelationshipAnalyzer...")
    relationship_analyzer = RelationshipAnalyzer()
    result = relationship_analyzer.analyze(
        user_msg, bot_msg, mock_llm_callable, conversation_history=[]
    )
    print(f"✅ Success: {result.success}")
    print(f"📊 Data: {result.data}")


def test_analysis_manager():
    """Test full pipeline with AnalysisManager."""
    print("\n" + "=" * 70)
    print("Testing AnalysisManager Pipeline")
    print("=" * 70)

    # Create manager with all analyzers
    manager = AnalysisManager(
        analyzers=[
            MoodAnalyzer(),
            SentimentAnalyzer(),
            RelationshipAnalyzer(),
        ],
        parallel=False,
    )

    print(f"\n✅ Created manager with {len(manager.analyzers)} analyzers")

    # Simulate conversation
    exchanges = [
        (
            "my neck and back are killing me. tons of pain",
            "I'm sorry to hear that. Have you tried any specific exercises?",
        ),
        (
            "yes i've already tried stretching",
            "I see. Have you tried any specific exercises or stretches?",
        ),
    ]

    for i, (user_msg, bot_msg) in enumerate(exchanges, 1):
        print(f"\n📨 Exchange {i}:")
        print(f"   User: {user_msg}")
        print(f"   Bot: {bot_msg}")

        context = manager.analyze(
            user_message=user_msg,
            bot_response=bot_msg,
            llm_callable=mock_llm_callable,
            conversation_history=[],
        )

        print(f"\n📊 Analysis Results:")
        print(f"   Message count: {context.message_count}")

        if context.mood:
            print(
                f"   Mood: {context.mood.get('primary_emotion')} "
                f"{context.mood.get('emoji')} "
                f"(engagement: {context.mood.get('engagement'):.2f})"
            )

        if context.sentiment:
            print(
                f"   User sentiment: {context.sentiment.get('sentiment')} "
                f"(needs: {', '.join(context.sentiment.get('user_needs', []))})"
            )

        if context.relationship:
            print(
                f"   Relationship: {context.relationship.get('level')} "
                f"(trust: {context.relationship.get('trust'):.2f})"
            )


def test_conditional_execution():
    """Test that analyzers skip when they should."""
    print("\n" + "=" * 70)
    print("Testing Conditional Execution")
    print("=" * 70)

    manager = AnalysisManager(
        analyzers=[
            MoodAnalyzer(),  # Runs every 2 messages
            RelationshipAnalyzer(),  # Runs every 5 messages
        ]
    )

    for i in range(1, 7):
        print(f"\n📨 Message {i}:")

        context = manager.analyze(
            user_message=f"Message {i}",
            bot_response=f"Response {i}",
            llm_callable=mock_llm_callable,
        )

        # Show which analyzers ran
        ran = [name for name, result in context.raw_results.items()]
        print(f"   Analyzers ran: {', '.join(ran) if ran else 'none'}")


def test_prompt_injection():
    """Show how analysis context would be injected into prompts."""
    print("\n" + "=" * 70)
    print("Testing Prompt Context Injection (Simulation)")
    print("=" * 70)

    manager = AnalysisManager(
        analyzers=[MoodAnalyzer(), SentimentAnalyzer(), RelationshipAnalyzer()]
    )

    context = manager.analyze(
        user_message="I'm so frustrated with this",
        bot_response="I understand. Let's work through it together.",
        llm_callable=mock_llm_callable,
    )

    print("\n📝 Context that would be injected into system prompt:")
    print("------")

    if context.mood:
        mood = context.mood
        print(
            f"Your current mood: {mood.get('primary_emotion')} {mood.get('emoji')}"
        )
        print(f"  → {mood.get('description')}")

        valence = mood.get("valence", 0.5)
        engagement = mood.get("engagement", 0.5)

        if valence < 0.3:
            print("  → You're feeling somewhat negative; be empathetic")
        elif valence > 0.7:
            print("  → You're feeling quite positive; convey warmth")

        if engagement > 0.7:
            print(
                "  → You're highly engaged; show curiosity and ask follow-ups"
            )

    if context.sentiment:
        sentiment = context.sentiment
        user_needs = sentiment.get("user_needs", [])
        print(f"\nUser appears {sentiment.get('sentiment')}")
        if user_needs:
            print(f"  → User needs: {', '.join(user_needs)}")

    if context.relationship:
        rel = context.relationship
        print(f"\nRelationship level: {rel.get('level')}")
        formality = rel.get("formality", 0.7)
        if formality > 0.7:
            print("  → Maintain formal, respectful tone")
        elif formality < 0.3:
            print("  → Use casual, friendly tone")

    print("------")


if __name__ == "__main__":
    print("🧪 Conversation Analysis System - Test Suite\n")

    # Run tests
    test_individual_analyzers()
    test_analysis_manager()
    test_conditional_execution()
    test_prompt_injection()

    print("\n" + "=" * 70)
    print("✅ All tests completed!")
    print("=" * 70)
    print(
        "\nNext steps:\n"
        "1. Integrate into BaseAgent (see INTEGRATION_EXAMPLE.py)\n"
        "2. Test with real LLM\n"
        "3. Tune analyzer settings\n"
        "4. Add more analyzers as needed"
    )
