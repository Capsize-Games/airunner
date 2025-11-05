"""
Unit tests for CodeAgent.
"""

from unittest.mock import Mock

from airunner.components.llm.agents.code_agent import (
    CodeAgent,
    CodeState,
)


class TestCodeAgent:
    """Test CodeAgent functionality."""

    def test_initialization(self):
        """Test Code agent initializes correctly."""
        mock_model = Mock()
        mock_model.bind_tools = Mock(return_value=mock_model)

        agent = CodeAgent(chat_model=mock_model)

        assert agent._chat_model is not None
        assert agent._system_prompt is not None
        assert isinstance(agent._tools, list)

    def test_custom_system_prompt(self):
        """Test custom system prompt is used."""
        mock_model = Mock()
        custom_prompt = "Custom code prompt"

        agent = CodeAgent(chat_model=mock_model, system_prompt=custom_prompt)

        assert agent._system_prompt == custom_prompt

    def test_analyze_code_request_python_write(self):
        """Test analyzing a Python code writing request."""
        from langchain_core.messages import HumanMessage

        mock_model = Mock()
        agent = CodeAgent(chat_model=mock_model)

        state = CodeState(
            messages=[
                HumanMessage(content="Write a Python function to sort a list")
            ],
            programming_language="",
            task_type="",
            execution_context={},
        )

        result = agent._analyze_code_request(state)

        assert result["programming_language"] == "python"
        assert result["task_type"] == "write"
        assert result["execution_context"]["safe_mode"] is True

    def test_analyze_code_request_javascript_debug(self):
        """Test analyzing a JavaScript debug request."""
        from langchain_core.messages import HumanMessage

        mock_model = Mock()
        agent = CodeAgent(chat_model=mock_model)

        state = CodeState(
            messages=[
                HumanMessage(content="Debug this JavaScript error in my code")
            ],
            programming_language="",
            task_type="",
            execution_context={},
        )

        result = agent._analyze_code_request(state)

        assert result["programming_language"] == "javascript"
        assert result["task_type"] == "debug"

    def test_analyze_code_request_rust_review(self):
        """Test analyzing a Rust code review request."""
        from langchain_core.messages import HumanMessage

        mock_model = Mock()
        agent = CodeAgent(chat_model=mock_model)

        state = CodeState(
            messages=[
                HumanMessage(content="Review my Rust code for best practices")
            ],
            programming_language="",
            task_type="",
            execution_context={},
        )

        result = agent._analyze_code_request(state)

        assert result["programming_language"] == "rust"
        assert result["task_type"] == "review"

    def test_analyze_code_request_java_explain(self):
        """Test analyzing a Java explanation request."""
        from langchain_core.messages import HumanMessage

        mock_model = Mock()
        agent = CodeAgent(chat_model=mock_model)

        state = CodeState(
            messages=[
                HumanMessage(content="Explain how Java interfaces work")
            ],
            programming_language="",
            task_type="",
            execution_context={},
        )

        result = agent._analyze_code_request(state)

        assert result["programming_language"] == "java"
        assert result["task_type"] == "explain"

    def test_execution_context_file_ops_allowed(self):
        """Test execution context allows file ops for write tasks."""
        from langchain_core.messages import HumanMessage

        mock_model = Mock()
        agent = CodeAgent(chat_model=mock_model)

        state = CodeState(
            messages=[HumanMessage(content="Create a Python file")],
            programming_language="",
            task_type="",
            execution_context={},
        )

        result = agent._analyze_code_request(state)

        assert result["execution_context"]["allow_file_ops"] is True

    def test_route_after_model_with_tool_calls(self):
        """Test routing when model requests tool usage."""
        from langchain_core.messages import AIMessage

        mock_model = Mock()
        agent = CodeAgent(chat_model=mock_model)

        # Create message with tool calls
        mock_message = Mock(spec=AIMessage)
        mock_message.tool_calls = [{"name": "execute_python", "args": {}}]

        state = CodeState(
            messages=[mock_message],
            programming_language="python",
            task_type="write",
            execution_context={},
        )

        route = agent._route_after_model(state)

        assert route == "tools"

    def test_route_after_model_without_tool_calls(self):
        """Test routing when model doesn't request tools."""
        from langchain_core.messages import AIMessage

        mock_model = Mock()
        agent = CodeAgent(chat_model=mock_model)

        state = CodeState(
            messages=[AIMessage(content="Here's the code...")],
            programming_language="python",
            task_type="write",
            execution_context={},
        )

        route = agent._route_after_model(state)

        assert route == "end"

    def test_build_graph(self):
        """Test that graph builds successfully."""
        mock_model = Mock()
        mock_model.bind_tools = Mock(return_value=mock_model)

        agent = CodeAgent(chat_model=mock_model)
        graph = agent.build_graph()

        assert graph is not None

    def test_compile_graph(self):
        """Test that graph compiles successfully."""
        mock_model = Mock()
        mock_model.bind_tools = Mock(return_value=mock_model)

        agent = CodeAgent(chat_model=mock_model)
        compiled = agent.compile()

        assert compiled is not None
