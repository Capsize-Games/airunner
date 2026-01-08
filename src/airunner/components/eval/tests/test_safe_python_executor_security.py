import pytest

from airunner.components.eval.math_tools import SafePythonExecutor


def test_executor_rejects_builtins_access():
    ex = SafePythonExecutor(timeout_seconds=1)

    ok, _, err = ex.execute('__builtins__["eval"]("1+1")')
    assert ok is False
    assert "builtins" in err.lower() or "__builtins__" in err.lower()


def test_executor_rejects_direct___import___call():
    ex = SafePythonExecutor(timeout_seconds=1)

    ok, _, err = ex.execute('__import__("os")')
    assert ok is False
    assert "__import__" in err.lower()


def test_executor_allows_math_import_and_use():
    ex = SafePythonExecutor(timeout_seconds=1)

    ok, result, err = ex.execute("import math; result = math.sqrt(9)")
    assert ok is True, err
    assert result == 3.0
