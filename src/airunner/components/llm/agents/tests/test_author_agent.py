"""
Unit tests for AuthorAgent.
"""

from unittest.mock import Mock

from airunner.components.llm.agents.author_agent import (
    AuthorAgent,
    AuthorState,
)


class TestAuthorAgent:
    """Test AuthorAgent functionality."""

    def test_initialization(self):
        """Test Author agent initializes correctly."""
        mock_model = Mock()
        mock_model.bind_tools = Mock(return_value=mock_model)

        agent = AuthorAgent(chat_model=mock_model)

        assert agent._chat_model is not None
        assert agent._system_prompt is not None
        assert isinstance(agent._tools, list)

    def test_custom_system_prompt(self):
        """Test custom system prompt is used."""
        mock_model = Mock()
        custom_prompt = "Custom author prompt"

        agent = AuthorAgent(chat_model=mock_model, system_prompt=custom_prompt)

        assert agent._system_prompt == custom_prompt

    def test_analyze_writing_request_story(self):
        """Test analyzing a story writing request."""
        from langchain_core.messages import HumanMessage

        mock_model = Mock()
        agent = AuthorAgent(chat_model=mock_model)

        state = AuthorState(
            messages=[
                HumanMessage(
                    content="Help me write a creative story about dragons"
                )
            ],
            writing_style="",
            content_type="",
        )

        result = agent._analyze_writing_request(state)

        assert result["writing_style"] == "creative"
        assert result["content_type"] == "story"

    def test_analyze_writing_request_formal_essay(self):
        """Test analyzing a formal essay request."""
        from langchain_core.messages import HumanMessage

        mock_model = Mock()
        agent = AuthorAgent(chat_model=mock_model)

        state = AuthorState(
            messages=[
                HumanMessage(content="Write a formal essay on climate change")
            ],
            writing_style="",
            content_type="",
        )

        result = agent._analyze_writing_request(state)

        assert result["writing_style"] == "formal"
        assert result["content_type"] == "essay"

    def test_analyze_writing_request_casual_article(self):
        """Test analyzing a casual article request."""
        from langchain_core.messages import HumanMessage

        mock_model = Mock()
        agent = AuthorAgent(chat_model=mock_model)

        state = AuthorState(
            messages=[
                HumanMessage(
                    content="Write a casual blog article about cooking"
                )
            ],
            writing_style="",
            content_type="",
        )

        result = agent._analyze_writing_request(state)

        assert result["writing_style"] == "casual"
        assert result["content_type"] == "article"

    def test_route_after_model_with_tool_calls(self):
        """Test routing when model requests tool usage."""
        from langchain_core.messages import AIMessage

        mock_model = Mock()
        agent = AuthorAgent(chat_model=mock_model)

        # Create message with tool calls
        mock_message = Mock(spec=AIMessage)
        mock_message.tool_calls = [{"name": "check_grammar", "args": {}}]

        state = AuthorState(
            messages=[mock_message],
            writing_style="general",
            content_type="general",
        )

        route = agent._route_after_model(state)

        assert route == "tools"

    def test_route_after_model_without_tool_calls(self):
        """Test routing when model doesn't request tools."""
        from langchain_core.messages import AIMessage

        mock_model = Mock()
        agent = AuthorAgent(chat_model=mock_model)

        state = AuthorState(
            messages=[AIMessage(content="Here's your story...")],
            writing_style="general",
            content_type="general",
        )

        route = agent._route_after_model(state)

        assert route == "end"

    def test_build_graph(self):
        """Test that graph builds successfully."""
        mock_model = Mock()
        mock_model.bind_tools = Mock(return_value=mock_model)

        agent = AuthorAgent(chat_model=mock_model)
        graph = agent.build_graph()

        assert graph is not None

    def test_compile_graph(self):
        """Test that graph compiles successfully."""
        mock_model = Mock()
        mock_model.bind_tools = Mock(return_value=mock_model)

        agent = AuthorAgent(chat_model=mock_model)
        compiled = agent.compile()

        assert compiled is not None
