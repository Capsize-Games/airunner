"""
Unit tests for mode_router module.
"""


from airunner.components.llm.managers.mode_router import (
    parse_intent_response,
    route_by_intent,
    UserIntent,
)


class TestParseIntentResponse:
    """Test intent response parsing."""

    def test_parse_valid_author_response(self):
        """Test parsing a valid author mode response."""
        response = """
        MODE: author
        CONFIDENCE: 0.9
        REASONING: User wants to write a story
        """
        intent = parse_intent_response(response)

        assert intent["mode"] == "author"
        assert intent["confidence"] == 0.9
        assert "story" in intent["reasoning"].lower()

    def test_parse_code_mode(self):
        """Test parsing code mode."""
        response = """
        MODE: code
        CONFIDENCE: 0.85
        REASONING: User needs help with Python
        """
        intent = parse_intent_response(response)

        assert intent["mode"] == "code"
        assert intent["confidence"] == 0.85

    def test_parse_research_mode(self):
        """Test parsing research mode."""
        response = """
        MODE: research
        CONFIDENCE: 0.75
        REASONING: User is gathering information
        """
        intent = parse_intent_response(response)

        assert intent["mode"] == "research"
        assert intent["confidence"] == 0.75

    def test_parse_qa_mode(self):
        """Test parsing QA mode."""
        response = """
        MODE: qa
        CONFIDENCE: 0.95
        REASONING: Direct factual question
        """
        intent = parse_intent_response(response)

        assert intent["mode"] == "qa"
        assert intent["confidence"] == 0.95

    def test_parse_general_mode(self):
        """Test parsing general mode."""
        response = """
        MODE: general
        CONFIDENCE: 0.6
        REASONING: Unclear intent
        """
        intent = parse_intent_response(response)

        assert intent["mode"] == "general"
        assert intent["confidence"] == 0.6

    def test_parse_invalid_mode_defaults_to_general(self):
        """Test that invalid mode falls back to general."""
        response = """
        MODE: invalid_mode
        CONFIDENCE: 0.8
        REASONING: Testing fallback
        """
        intent = parse_intent_response(response)

        assert intent["mode"] == "general"

    def test_parse_confidence_clipped_to_range(self):
        """Test that confidence is clipped to 0.0-1.0 range."""
        response = """
        MODE: author
        CONFIDENCE: 1.5
        REASONING: Testing bounds
        """
        intent = parse_intent_response(response)

        assert 0.0 <= intent["confidence"] <= 1.0

    def test_parse_malformed_response(self):
        """Test parsing malformed response."""
        response = "Some random text without proper format"
        intent = parse_intent_response(response)

        # Should have defaults
        assert intent["mode"] == "general"
        assert isinstance(intent["confidence"], float)
        assert isinstance(intent["reasoning"], str)


class TestRouteByIntent:
    """Test routing function."""

    def test_route_author(self):
        """Test routing to author mode."""
        state = {
            "intent": UserIntent(
                mode="author", confidence=0.9, reasoning="Writing task"
            )
        }

        route = route_by_intent(state)
        assert route == "author"

    def test_route_code(self):
        """Test routing to code mode."""
        state = {
            "intent": UserIntent(
                mode="code", confidence=0.85, reasoning="Coding task"
            )
        }

        route = route_by_intent(state)
        assert route == "code"

    def test_route_research(self):
        """Test routing to research mode."""
        state = {
            "intent": UserIntent(
                mode="research",
                confidence=0.8,
                reasoning="Research task",
            )
        }

        route = route_by_intent(state)
        assert route == "research"

    def test_route_qa(self):
        """Test routing to QA mode."""
        state = {
            "intent": UserIntent(
                mode="qa", confidence=0.95, reasoning="Question"
            )
        }

        route = route_by_intent(state)
        assert route == "qa"

    def test_route_general(self):
        """Test routing to general mode."""
        state = {
            "intent": UserIntent(
                mode="general", confidence=0.6, reasoning="Unclear"
            )
        }

        route = route_by_intent(state)
        assert route == "general"

    def test_route_no_intent_defaults_general(self):
        """Test that missing intent routes to general."""
        state = {}

        route = route_by_intent(state)
        assert route == "general"
