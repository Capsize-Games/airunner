"""
Eval tests for Code Mode with natural language prompts.

Tests that the mode-based routing correctly identifies code intent
and routes to the CodeAgent which uses code-specific tools like:
- execute_python()
- format_code()
- lint_code()
- analyze_code_complexity()
- create_code_file()
- read_code_file()
"""

import pytest
import logging
from airunner.components.eval.utils.tracking import track_trajectory_sync
from airunner.components.eval.utils.trajectory_evaluator import (
    trajectory_contains,
)

logger = logging.getLogger(__name__)

pytestmark = [
    pytest.mark.eval,
    pytest.mark.timeout(60),
]


@pytest.mark.eval
class TestCodeModeEval:
    """Eval tests for Code Mode natural language triggering."""

    def test_python_execution_basic(
        self,
        airunner_client_function_scope,
    ):
        """Test that Python execution request routes to code mode."""
        prompt = "Execute this Python code: print(2 + 2)"

        result = track_trajectory_sync(
            airunner_client_function_scope,
            prompt=prompt,
            max_tokens=500,
            use_mode_routing=True,
        )

        response = result["response"]
        tools = result["tools"]

        # Verify response includes execution result
        response_text = (
            response.lower()
            if isinstance(response, str)
            else response.get("text", "").lower()
        )
        assert any(
            keyword in response_text
            for keyword in ["4", "result", "output", "execute"]
        ), f"Response doesn't show execution result: {response_text}"

        # Verify execute_python tool was used
        assert trajectory_contains(
            result, "execute_python"
        ), f"Expected execute_python tool, got: {tools}"

    def test_code_formatting(
        self,
        airunner_client_function_scope,
    ):
        """Test that code formatting request routes to code mode."""
        prompt = "Format this Python code: " "def foo(x,y):return x+y"

        result = track_trajectory_sync(
            airunner_client_function_scope,
            prompt=prompt,
            max_tokens=500,
            use_mode_routing=True,
        )

        response = result["response"]
        tools = result["tools"]

        # Verify response includes formatted code
        response_text = (
            response.lower()
            if isinstance(response, str)
            else response.get("text", "").lower()
        )
        assert any(
            keyword in response_text
            for keyword in ["formatted", "def foo", "return"]
        ), f"Response doesn't show formatted code: {response_text}"

        # Verify format_code tool was used
        assert trajectory_contains(
            result, "format_code"
        ), f"Expected format_code tool, got: {tools}"

    def test_code_linting(
        self,
        airunner_client_function_scope,
    ):
        """Test that code linting request routes to code mode."""
        prompt = (
            "Lint this Python code: "
            "def foo():\n"
            "    unused_var = 5\n"
            "    return 10"
        )

        result = track_trajectory_sync(
            airunner_client_function_scope,
            prompt=prompt,
            max_tokens=500,
            use_mode_routing=True,
        )

        response = result["response"]
        tools = result["tools"]

        # Verify response addresses linting
        response_text = (
            response.lower()
            if isinstance(response, str)
            else response.get("text", "").lower()
        )
        assert any(
            keyword in response_text
            for keyword in ["lint", "unused", "warning", "issue"]
        ), f"Response doesn't address linting: {response_text}"

        # Verify lint_code tool was used
        assert trajectory_contains(
            result, "lint_code"
        ), f"Expected lint_code tool, got: {tools}"

    def test_complexity_analysis(
        self,
        airunner_client_function_scope,
    ):
        """Test that complexity analysis request routes to code mode."""
        prompt = (
            "Analyze the complexity of this code: "
            "def fibonacci(n):\n"
            "    if n <= 1:\n"
            "        return n\n"
            "    return fibonacci(n-1) + fibonacci(n-2)"
        )

        result = track_trajectory_sync(
            airunner_client_function_scope,
            prompt=prompt,
            max_tokens=500,
            use_mode_routing=True,
        )

        response = result["response"]
        tools = result["tools"]

        # Verify response analyzes complexity
        response_text = (
            response.lower()
            if isinstance(response, str)
            else response.get("text", "").lower()
        )
        assert any(
            keyword in response_text
            for keyword in [
                "complexity",
                "recursive",
                "exponential",
                "cyclomatic",
            ]
        ), f"Response doesn't analyze complexity: {response_text}"

        # Verify analyze_code_complexity tool was used
        assert trajectory_contains(
            result, "analyze_code_complexity"
        ), f"Expected analyze_code_complexity tool, got: {tools}"

    def test_file_operations(
        self,
        airunner_client_function_scope,
    ):
        """Test that file operations route to code mode."""
        prompt = (
            "Create a Python file called test.py with a hello world function"
        )

        result = track_trajectory_sync(
            airunner_client_function_scope,
            prompt=prompt,
            max_tokens=500,
            use_mode_routing=True,
        )

        response = result["response"]
        tools = result["tools"]

        # Verify response addresses file creation
        response_text = (
            response.lower()
            if isinstance(response, str)
            else response.get("text", "").lower()
        )
        assert any(
            keyword in response_text
            for keyword in ["created", "file", "test.py", "hello"]
        ), f"Response doesn't address file creation: {response_text}"

        # Verify create_code_file tool was used
        assert trajectory_contains(
            result, "create_code_file"
        ), f"Expected create_code_file tool, got: {tools}"

    def test_code_mode_trajectory_efficiency(
        self,
        airunner_client_function_scope,
    ):
        """Test that code mode uses efficient tool paths."""
        prompt = (
            "Execute and format this code: "
            "def add(a,b):return a+b\n"
            "print(add(2,3))"
        )

        result = track_trajectory_sync(
            airunner_client_function_scope,
            prompt=prompt,
            max_tokens=500,
            use_mode_routing=True,
        )

        trajectory = result["trajectory"]
        tools = result["tools"]

        # Verify trajectory is efficient
        assert (
            len(trajectory) < 10
        ), f"Trajectory too long (inefficient): {trajectory}"

        # Verify appropriate code tools used
        code_tools_used = [
            t
            for t in tools
            if t
            in [
                "execute_python",
                "format_code",
                "lint_code",
                "analyze_code_complexity",
                "create_code_file",
                "read_code_file",
            ]
        ]
        assert len(code_tools_used) > 0, f"No code tools used: {tools}"
