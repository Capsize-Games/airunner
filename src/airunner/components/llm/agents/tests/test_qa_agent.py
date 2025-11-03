"""
Unit tests for QAAgent.
"""

from unittest.mock import Mock

from airunner.components.llm.agents.qa_agent import (
    QAAgent,
    QAState,
)


class TestQAAgent:
    """Test QAAgent functionality."""

    def test_initialization(self):
        """Test QA agent initializes correctly."""
        mock_model = Mock()
        mock_model.bind_tools = Mock(return_value=mock_model)

        agent = QAAgent(chat_model=mock_model)

        assert agent._chat_model is not None
        assert agent._system_prompt is not None
        assert isinstance(agent._tools, list)

    def test_custom_system_prompt(self):
        """Test custom system prompt is used."""
        mock_model = Mock()
        custom_prompt = "Custom QA prompt"

        agent = QAAgent(chat_model=mock_model, system_prompt=custom_prompt)

        assert agent._system_prompt == custom_prompt

    def test_analyze_question_factual(self):
        """Test analyzing a factual question."""
        from langchain_core.messages import HumanMessage

        mock_model = Mock()
        agent = QAAgent(chat_model=mock_model)

        state = QAState(
            messages=[HumanMessage(content="What is the capital of France?")],
            question_type="",
            requires_verification=False,
            confidence_threshold=0.0,
        )

        result = agent._analyze_question(state)

        assert result["question_type"] == "factual"
        assert result["requires_verification"] is True

    def test_analyze_question_explanation(self):
        """Test analyzing an explanation question."""
        from langchain_core.messages import HumanMessage

        mock_model = Mock()
        agent = QAAgent(chat_model=mock_model)

        state = QAState(
            messages=[HumanMessage(content="Why does the sun shine?")],
            question_type="",
            requires_verification=False,
            confidence_threshold=0.0,
        )

        result = agent._analyze_question(state)

        assert result["question_type"] == "explanation"
        assert result["confidence_threshold"] == 0.6

    def test_analyze_question_person(self):
        """Test analyzing a person-related question."""
        from langchain_core.messages import HumanMessage

        mock_model = Mock()
        agent = QAAgent(chat_model=mock_model)

        state = QAState(
            messages=[HumanMessage(content="Who invented the telephone?")],
            question_type="",
            requires_verification=False,
            confidence_threshold=0.0,
        )

        result = agent._analyze_question(state)

        assert result["question_type"] == "person"

    def test_analyze_question_verification(self):
        """Test analyzing a verification question."""
        from langchain_core.messages import HumanMessage

        mock_model = Mock()
        agent = QAAgent(chat_model=mock_model)

        state = QAState(
            messages=[
                HumanMessage(content="Is it true that water boils at 100°C?")
            ],
            question_type="",
            requires_verification=False,
            confidence_threshold=0.0,
        )

        result = agent._analyze_question(state)

        assert result["question_type"] == "verification"
        assert result["requires_verification"] is True
        assert result["confidence_threshold"] == 0.9

    def test_analyze_question_temporal_spatial(self):
        """Test analyzing temporal/spatial question."""
        from langchain_core.messages import HumanMessage

        mock_model = Mock()
        agent = QAAgent(chat_model=mock_model)

        state = QAState(
            messages=[HumanMessage(content="When did World War II end?")],
            question_type="",
            requires_verification=False,
            confidence_threshold=0.0,
        )

        result = agent._analyze_question(state)

        assert result["question_type"] == "temporal_spatial"
        assert result["requires_verification"] is True

    def test_route_after_model_with_tool_calls(self):
        """Test routing when model requests tool usage."""
        from langchain_core.messages import AIMessage

        mock_model = Mock()
        agent = QAAgent(chat_model=mock_model)

        # Create message with tool calls
        mock_message = Mock(spec=AIMessage)
        mock_message.tool_calls = [{"name": "verify_answer", "args": {}}]

        state = QAState(
            messages=[mock_message],
            question_type="factual",
            requires_verification=True,
            confidence_threshold=0.7,
        )

        route = agent._route_after_model(state)

        assert route == "tools"

    def test_route_after_model_without_tool_calls(self):
        """Test routing when model doesn't request tools."""
        from langchain_core.messages import AIMessage

        mock_model = Mock()
        agent = QAAgent(chat_model=mock_model)

        state = QAState(
            messages=[AIMessage(content="The answer is...")],
            question_type="factual",
            requires_verification=False,
            confidence_threshold=0.7,
        )

        route = agent._route_after_model(state)

        assert route == "end"

    def test_build_graph(self):
        """Test that graph builds successfully."""
        mock_model = Mock()
        mock_model.bind_tools = Mock(return_value=mock_model)

        agent = QAAgent(chat_model=mock_model)
        graph = agent.build_graph()

        assert graph is not None

    def test_compile_graph(self):
        """Test that graph compiles successfully."""
        mock_model = Mock()
        mock_model.bind_tools = Mock(return_value=mock_model)

        agent = QAAgent(chat_model=mock_model)
        compiled = agent.compile()

        assert compiled is not None
