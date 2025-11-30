"""
Mathematical computation tools for LLM agents.

Provides symbolic math (SymPy), numerical computation (NumPy/SciPy),
and general Python calculation tools for solving math problems.
"""

from contextlib import contextmanager
import contextvars
from typing import Annotated, Iterator, Tuple
from airunner.components.llm.core.tool_registry import tool, ToolCategory
from airunner.components.eval.math_tools import (
    SafePythonExecutor,
    set_executor_session,
    reset_executor_session,
)


# Shared executor instance
_executor = SafePythonExecutor()


def _session_namespace_key(session_id: str) -> str:
    """Return namespace key for executor session."""

    return session_id or "global"


def start_math_executor_session(
    session_id: str,
) -> Tuple[str, contextvars.Token[str]]:
    """Start a math executor session and return context data."""

    namespace_key = _session_namespace_key(session_id)
    token = set_executor_session(namespace_key)
    _executor.reset(namespace_key)
    return namespace_key, token


def end_math_executor_session(
    session_data: Tuple[str, contextvars.Token[str]],
) -> None:
    """End the math executor session and clean namespace."""

    namespace_key, token = session_data
    _executor.reset(namespace_key)
    reset_executor_session(token)


@contextmanager
def math_executor_session(session_id: str) -> Iterator[None]:
    """Context manager ensuring isolated math executor session per request."""

    if not session_id:
        yield
        return

    session_data = start_math_executor_session(session_id)
    try:
        yield
    finally:
        end_math_executor_session(session_data)


@tool(
    name="sympy_compute",
    category=ToolCategory.MATH,
    description="Execute SymPy symbolic mathematics code for solving equations, symbolic algebra, calculus, exact fractions",
    return_direct=False,
    requires_api=False,
)
def sympy_compute(
    code: Annotated[
        str,
        "Python code using SymPy. Must store final result in 'result' variable.",
    ],
) -> str:
    """Execute SymPy symbolic math code.

    Args:
        code: Python code using SymPy library

    """
    try:
        # Ensure sympy is imported
        if "import sympy" not in code and "from sympy" not in code:
            code = "import sympy as sp\n" + code

        result = _executor.execute(code)
        return f"SymPy result: {result}"
    except Exception as e:
        return f"SymPy error: {e}"


@tool(
    name="numpy_compute",
    category=ToolCategory.MATH,
    description="Execute NumPy/SciPy numerical computations for linear algebra, matrix operations, numerical methods",
    return_direct=False,
    requires_api=False,
)
def numpy_compute(
    code: Annotated[
        str,
        "Python code using NumPy/SciPy. Must store final result in 'result' variable.",
    ],
) -> str:
    """Execute NumPy/SciPy numerical computation.

    Args:
        code: Python code using NumPy/SciPy libraries

    """
    try:
        # Ensure numpy is imported
        if "import numpy" not in code and "from numpy" not in code:
            code = "import numpy as np\n" + code

        result = _executor.execute(code)
        return f"NumPy result: {result}"
    except Exception as e:
        return f"NumPy error: {e}"


@tool(
    name="python_compute",
    category=ToolCategory.MATH,
    description="Execute general Python code for calculations, using math, fractions, decimal modules",
    return_direct=False,
    requires_api=False,
)
def python_compute(
    code: Annotated[
        str,
        "Python code for calculations. Must store final result in 'result' variable.",
    ],
) -> str:
    """Execute general Python calculation.

    Args:
        code: Python code for mathematical calculation

    """
    try:
        result = _executor.execute(code)
        return f"Python result: {result}"
    except Exception as e:
        return f"Python error: {e}"
