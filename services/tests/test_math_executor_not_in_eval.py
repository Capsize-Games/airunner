"""Regression test for issue #2189.

Production LLM tools (sympy_compute/numpy_compute/python_compute in
services/src/airunner_services/llm/tools/math_tools.py) previously
imported SafePythonExecutor from airunner_services.eval.math_tools,
so a production code-execution sandbox lived in benchmark-support
code and nothing outside eval/ could safely depend on eval/. The
executor moved to airunner_services.llm.core.math_executor; this
test pins the inversion and re-checks its safety behaviour still
holds at the new location, since that behaviour is the entire point
of the move.
"""

from __future__ import annotations

import re
from pathlib import Path

from airunner_services.llm.core.math_executor import (
    SafePythonExecutor,
    get_executor_session,
    reset_executor_session,
    set_executor_session,
)

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_SERVICES_SRC = _PROJECT_ROOT / "services" / "src" / "airunner_services"


_IMPORT_PATTERN = re.compile(
    r"^\s*(?:from|import)\s+airunner_services\.eval\b", re.MULTILINE
)


def test_nothing_outside_eval_imports_airunner_services_eval():
    """Only prose (e.g. a docstring noting the old location) may match.

    An actual `import`/`from` statement reaching into eval/ from
    outside it is what issue #2189 eliminated.
    """
    offenders = []
    for path in _SERVICES_SRC.rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        if path.parts[len(_SERVICES_SRC.parts)] == "eval":
            continue
        text = path.read_text()
        if _IMPORT_PATTERN.search(text):
            offenders.append(str(path))
    assert offenders == []


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


def test_self_verification_solver_still_uses_the_moved_executor():
    from airunner_services.eval.math_tools import SelfVerificationSolver

    solver = SelfVerificationSolver(client=None)
    assert isinstance(solver.executor, SafePythonExecutor)
