"""
Unit tests for ResearchAgent.
"""

from unittest.mock import Mock

from airunner.components.llm.agents.research_agent import (
    ResearchAgent,
    ResearchState,
)


class TestResearchAgent:
    """Test ResearchAgent functionality."""

    def test_initialization(self):
        """Test Research agent initializes correctly."""
        mock_model = Mock()
        mock_model.bind_tools = Mock(return_value=mock_model)

        agent = ResearchAgent(chat_model=mock_model)

        assert agent._chat_model is not None
        assert agent._system_prompt is not None
        assert isinstance(agent._tools, list)

    def test_custom_system_prompt(self):
        """Test custom system prompt is used."""
        mock_model = Mock()
        custom_prompt = "Custom research prompt"

        agent = ResearchAgent(
            chat_model=mock_model, system_prompt=custom_prompt
        )

        assert agent._system_prompt == custom_prompt

    def test_plan_research_default(self):
        """Test research planning with default values."""
        from langchain_core.messages import HumanMessage

        mock_model = Mock()
        agent = ResearchAgent(chat_model=mock_model)

        state = ResearchState(
            messages=[HumanMessage(content="Research climate change")],
            research_topic="",
            source_count=0,
            citation_style="",
        )

        result = agent._plan_research(state)

        assert isinstance(result["research_topic"], str)
        assert result["source_count"] > 0
        assert result["citation_style"] in ["APA", "MLA", "Chicago"]

    def test_plan_research_mla_citation(self):
        """Test detecting MLA citation style."""
        from langchain_core.messages import HumanMessage

        mock_model = Mock()
        agent = ResearchAgent(chat_model=mock_model)

        state = ResearchState(
            messages=[HumanMessage(content="Research topic using MLA format")],
            research_topic="",
            source_count=0,
            citation_style="",
        )

        result = agent._plan_research(state)

        assert result["citation_style"] == "MLA"

    def test_plan_research_chicago_citation(self):
        """Test detecting Chicago citation style."""
        from langchain_core.messages import HumanMessage

        mock_model = Mock()
        agent = ResearchAgent(chat_model=mock_model)

        state = ResearchState(
            messages=[
                HumanMessage(content="Find sources in Chicago citation style")
            ],
            research_topic="",
            source_count=0,
            citation_style="",
        )

        result = agent._plan_research(state)

        assert result["citation_style"] == "Chicago"

    def test_plan_research_many_sources(self):
        """Test detecting request for many sources."""
        from langchain_core.messages import HumanMessage

        mock_model = Mock()
        agent = ResearchAgent(chat_model=mock_model)

        state = ResearchState(
            messages=[
                HumanMessage(
                    content="Do comprehensive research with many sources"
                )
            ],
            research_topic="",
            source_count=0,
            citation_style="",
        )

        result = agent._plan_research(state)

        assert result["source_count"] >= 5

    def test_plan_research_few_sources(self):
        """Test detecting request for few sources."""
        from langchain_core.messages import HumanMessage

        mock_model = Mock()
        agent = ResearchAgent(chat_model=mock_model)

        state = ResearchState(
            messages=[HumanMessage(content="Quick research with few sources")],
            research_topic="",
            source_count=0,
            citation_style="",
        )

        result = agent._plan_research(state)

        assert result["source_count"] <= 2

    def test_route_after_model_with_tool_calls(self):
        """Test routing when model requests tool usage."""
        from langchain_core.messages import AIMessage

        mock_model = Mock()
        agent = ResearchAgent(chat_model=mock_model)

        # Create message with tool calls
        mock_message = Mock(spec=AIMessage)
        mock_message.tool_calls = [{"name": "synthesize_sources", "args": {}}]

        state = ResearchState(
            messages=[mock_message],
            research_topic="test",
            source_count=3,
            citation_style="APA",
        )

        route = agent._route_after_model(state)

        assert route == "tools"

    def test_route_after_model_without_tool_calls(self):
        """Test routing when model doesn't request tools."""
        from langchain_core.messages import AIMessage

        mock_model = Mock()
        agent = ResearchAgent(chat_model=mock_model)

        state = ResearchState(
            messages=[AIMessage(content="Here's the research...")],
            research_topic="test",
            source_count=3,
            citation_style="APA",
        )

        route = agent._route_after_model(state)

        assert route == "end"

    def test_build_graph(self):
        """Test that graph builds successfully."""
        mock_model = Mock()
        mock_model.bind_tools = Mock(return_value=mock_model)

        agent = ResearchAgent(chat_model=mock_model)
        graph = agent.build_graph()

        assert graph is not None

    def test_compile_graph(self):
        """Test that graph compiles successfully."""
        mock_model = Mock()
        mock_model.bind_tools = Mock(return_value=mock_model)

        agent = ResearchAgent(chat_model=mock_model)
        compiled = agent.compile()

        assert compiled is not None
