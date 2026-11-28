"""Regression tests for issue #2491.

The math executor must run validated code in a confined subprocess
(``math_worker.py``) with resource limits and a wall-clock timeout,
instead of exec'ing it on a thread in the service process. A leaked
thread cannot be killed, so only the subprocess boundary contains
tight C-level loops and runaway allocations.
"""

from __future__ import annotations

import ast
import importlib.util
import os
import time
from unittest import mock

from airunner_services.llm.core.math_executor import (
    SafePythonExecutor,
    reset_executor_session,
    set_executor_session,
)


def _load_worker_module():
    """Load math_worker.py by path (it never imports the package)."""
    import airunner_services.llm.core.math_executor as executor_mod

    path = os.path.join(
        os.path.dirname(os.path.abspath(executor_mod.__file__)),
        "math_worker.py",
    )
    spec = importlib.util.spec_from_file_location(
        "math_worker_under_test", path
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_math_runs_in_confined_subprocess():
    executor = SafePythonExecutor()
    ok, result, err = executor.execute("result = 2 + 2")
    assert ok is True
    assert result == 4
    assert err == ""
    assert executor.last_worker_pid is not None
    assert executor.last_worker_pid != os.getpid()


def test_confined_timeout_kills_tight_loop():
    executor = SafePythonExecutor(timeout_seconds=2)
    start = time.monotonic()
    ok, result, err = executor.execute("while True:\n    pass")
    elapsed = time.monotonic() - start
    assert ok is False
    assert result is None
    assert "timed out" in err
    # The worker was killed on the wall clock instead of leaking.
    assert elapsed < 20
    # The parent is still healthy afterwards.
    ok, result, err = executor.execute("result = 40 + 2")
    assert (ok, result, err) == (True, 42, "")


def test_confined_memory_limit_enforced():
    executor = SafePythonExecutor(timeout_seconds=10)
    start = time.monotonic()
    ok, result, err = executor.execute("result = [0] * (10 ** 10)")
    elapsed = time.monotonic() - start
    assert ok is False
    assert result is None
    assert err
    # The 80 GiB grab fails fast against the address-space ceiling.
    assert elapsed < 20
    ok, result, err = executor.execute("result = 7 * 6")
    assert (ok, result, err) == (True, 42, "")


def test_unsafe_code_rejected_without_spawn():
    executor = SafePythonExecutor()
    with mock.patch("subprocess.Popen") as popen:
        ok, _result, err = executor.execute("import os")
    assert ok is False
    assert "os" in err
    popen.assert_not_called()
    assert executor.last_worker_pid is None


def test_session_state_replays_across_calls():
    executor = SafePythonExecutor()
    token = set_executor_session("confinement-replay")
    try:
        ok, _res, err = executor.execute("x = 41")
        assert ok is True, err
        ok, result, err = executor.execute("result = x + 1")
        assert ok is True, err
        assert result == 42
    finally:
        executor.reset("confinement-replay")
        reset_executor_session(token)


def test_session_reset_clears_replay():
    executor = SafePythonExecutor()
    token = set_executor_session("confinement-reset")
    try:
        assert executor.execute("x = 41")[0] is True
        executor.reset("confinement-reset")
        ok, _res, err = executor.execute("result = x + 1")
        assert ok is False
        assert "x" in err
    finally:
        reset_executor_session(token)


def test_namespace_pollution_controlled_in_shadow():
    import math as stdlib_math

    executor = SafePythonExecutor()
    token = set_executor_session("confinement-pollution")
    try:
        ok, _res, err = executor.execute("math = 999\nresult = 1")
        assert ok is True, err
        stored = executor._namespaces["confinement-pollution"]
        assert stored["math"] is stdlib_math
        assert [
            key
            for key in stored
            if key.startswith("__")
            and key.endswith("__")
            and key != "__builtins__"
        ] == []
    finally:
        executor.reset("confinement-pollution")
        reset_executor_session(token)


def test_child_parity_with_parent_policy():
    worker = _load_worker_module()
    assert set(worker.ALLOWED_IMPORTS) == set(
        SafePythonExecutor.ALLOWED_IMPORTS
    )
    assert set(worker._create_safe_builtins()) == set(
        SafePythonExecutor()._create_safe_builtins()
    )


def test_child_never_imports_service_package():
    import airunner_services.llm.core.math_executor as executor_mod

    path = os.path.join(
        os.path.dirname(os.path.abspath(executor_mod.__file__)),
        "math_worker.py",
    )
    tree = ast.parse(open(path, encoding="utf-8").read())
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(a.name.split(".", 1)[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.add((node.module or "").split(".", 1)[0])
    assert not {name for name in imported if "airunner" in name}
