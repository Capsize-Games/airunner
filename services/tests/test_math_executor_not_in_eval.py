"""Regression test for issue #2189.

Production LLM tools (sympy_compute/numpy_compute/python_compute in
services/src/airunner_services/llm/tools/math_tools.py) previously
imported SafePythonExecutor from airunner_services.eval.math_tools,
so a production code-execution sandbox lived in benchmark-support
code. The executor moved to airunner_services.llm.core.math_executor;
this test re-checks its safety behaviour still holds at the new
location, since that behaviour is the entire point of the move.

eval/ itself was later extracted to its own repository (issue #2194,
https://github.com/Capsize-Games/airunner-eval), so the two tests
that used to assert nothing outside eval/ imported it, and that
SelfVerificationSolver (which lived in eval/) still used the moved
executor, no longer have anything to check in this repository --
removed rather than left in a form that either imports a module that
no longer exists here or asserts something vacuously true.
"""

from __future__ import annotations

from airunner_services.llm.core.math_executor import (
    SafePythonExecutor,
    get_executor_session,
    reset_executor_session,
    set_executor_session,
)


def test_executor_allows_ordinary_math():
    executor = SafePythonExecutor()
    ok, result, err = executor.execute("result = 2 + 2")
    assert ok is True
    assert result == 4
    assert err == ""


def test_executor_rejects_disallowed_import():
    executor = SafePythonExecutor()
    ok, _result, err = executor.execute("import os")
    assert ok is False
    assert "os" in err


def test_executor_rejects_forbidden_call():
    executor = SafePythonExecutor()
    ok, _result, err = executor.execute('exec("1")')
    assert ok is False
    assert "exec" in err


def test_executor_session_helpers_round_trip():
    token = set_executor_session("test-session")
    try:
        assert get_executor_session() == "test-session"
    finally:
        reset_executor_session(token)
    assert get_executor_session() == "global"
