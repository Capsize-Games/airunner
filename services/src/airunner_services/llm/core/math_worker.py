"""Confined math-code worker child (issue #2491).

Runs ONE math snippet in a fresh interpreter started by
``math_executor`` as ``sys.executable <this file>``: never forked,
never importing the service package (whose ``__init__`` chains pull
the agent stack). Only ``tool_worker_confine`` is loaded, by path,
for resource limits and capped stdout.

The parent sends ``{"history": [...], "code": ..., "timeout_ms": N}``
as JSON on stdin. ``history`` holds previously accepted snippets for
the session so variables persist across calls without ever pickling
values back into the parent. The worker replays the history with
discarded output, executes the new code, and writes one JSON reply::

    {"ok": bool, "result": <json-safe>, "stdout": str, "error": str,
     "bindings": {name: <json-safe>}, "pid": int, "limits": {...}}

``bindings`` carries the new code's top-level assignments encoded to
stay JSON-safe (native scalars round-trip exactly; anything else is
stringified), so the parent can keep an introspection cache without
unpickling child-influenced data. ``pid`` lets callers prove the code
ran off-process.
"""

from __future__ import annotations

import ast
import json
import math
import os
import sys
import tempfile
import traceback
from fractions import Fraction
from typing import Any

_CONFINE: Any = None

#: Mirrors SafePythonExecutor.ALLOWED_IMPORTS; pinned by parity test.
ALLOWED_IMPORTS = frozenset(
    {
        "math",
        "cmath",
        "fractions",
        "decimal",
        "statistics",
        "itertools",
        "sympy",
        "numpy",
        "scipy",
    }
)

#: Address-space ceiling: NumPy/SymPy reserve ~1 GiB of virtual
#: mappings at import, so the 512 MiB custom-tool default hangs them;
#: 2 GiB still fails multi-gigabyte grabs deterministically.
ADDRESS_SPACE_BYTES = 2 * 1024 * 1024 * 1024

#: Process-count limit is left alone (None): validated math code has
#: no spawn primitive, so a fork bomb is unreachable, while any fixed
#: RLIMIT_NPROC ceiling also forbids the BLAS thread pool (the limit
#: counts every process of the uid, and thread creation fails first).
MAX_PROCESSES = None

#: Hard cap on one stdin request (history + code).
MAX_REQUEST_BYTES = 1024 * 1024

#: Captured-stdout cap for the new code only.
OUTPUT_CAP_BYTES = 65536


def _load_confine() -> Any:
    """Load tool_worker_confine by path (no service-package import)."""
    global _CONFINE
    if _CONFINE is None:
        import importlib.util

        here = os.path.dirname(os.path.abspath(__file__))
        path = os.path.join(here, "tool_worker_confine.py")
        spec = importlib.util.spec_from_file_location(
            "w_math_confine", path
        )
        if spec is None or spec.loader is None:
            raise ImportError("cannot load tool_worker_confine")
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        _CONFINE = module
    return _CONFINE


def _safe_import(
    name: str,
    globals: Any = None,
    locals: Any = None,
    fromlist: Any = (),
    level: int = 0,
) -> Any:
    """Import hook allowing only top-level allow-listed modules."""
    if level != 0:
        raise ImportError("Relative imports are not allowed")
    top, _, _rest = name.partition(".")
    allowed = name == top and top in ALLOWED_IMPORTS
    if not allowed:
        raise ImportError(f"Import not allowed: {top}")
    return __import__(name, globals, locals, fromlist, level)


def _create_safe_builtins() -> dict[str, Any]:
    """Mirror SafePythonExecutor's restricted builtins."""
    return {
        "abs": abs,
        "round": round,
        "min": min,
        "max": max,
        "sum": sum,
        "len": len,
        "range": range,
        "int": int,
        "float": float,
        "str": str,
        "bool": bool,
        "list": list,
        "dict": dict,
        "set": set,
        "tuple": tuple,
        "pow": pow,
        "print": print,
        "__import__": _safe_import,
    }


def _create_base_namespace() -> dict[str, Any]:
    """Build a fresh namespace with safe builtins and defaults."""
    return {
        "__builtins__": _create_safe_builtins(),
        "math": math,
        "Fraction": Fraction,
    }


def _json_default(value: Any) -> Any:
    """Encode bytes and collections; stringify anything else."""
    if isinstance(value, bytes):
        return {"__bytes_b64__": value.decode("latin1")}
    if isinstance(value, (set, frozenset, tuple)):
        return list(value)
    return str(value)


def _json_safe(value: Any) -> Any:
    """Round-trip one value, falling back to its string form."""
    try:
        return json.loads(json.dumps(value, default=_json_default))
    except (TypeError, ValueError):
        return str(value)


def _parse_output_as_number(output: str) -> Any:
    """Parse the last stdout line as a number, else keep the text."""
    lines = output.split("\n")
    last_line = lines[-1].strip()
    try:
        return float(last_line)
    except ValueError:
        return last_line


def _extract_result(namespace: dict[str, Any], stdout_text: str) -> Any:
    """Mirror the executor's result/answer-var, then stdout, priority."""
    result = namespace.get("result") or namespace.get("answer")
    if result is None and stdout_text.strip():
        result = _parse_output_as_number(stdout_text.strip())
    return result


def _top_level_names(code: str) -> list[str]:
    """Collect names one snippet assigns at module level."""
    try:
        tree = ast.parse(code)
    except (SyntaxError, ValueError):
        return []
    names: list[str] = []

    def add_target(target: ast.AST) -> None:
        """Collect one assignment target's bound names."""
        if isinstance(target, ast.Name):
            names.append(target.id)
        elif isinstance(target, (ast.Tuple, ast.List)):
            for elt in target.elts:
                add_target(elt)

    for node in tree.body:
        if isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
            targets = (
                node.targets
                if isinstance(node, ast.Assign)
                else [node.target]
            )
            for target in targets:
                add_target(target)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef,
                               ast.ClassDef)):
            names.append(node.name)
        elif isinstance(node, (ast.For, ast.AsyncFor)):
            add_target(node.target)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            for alias in node.names:
                if alias.name == "*":
                    continue
                names.append(
                    alias.asname or alias.name.split(".", 1)[0]
                )
    seen: set[str] = set()
    return [n for n in names if not (n in seen or seen.add(n))]


def _isolate(timeout_ms: Any) -> dict[str, str]:
    """Chdir to an empty temp dir and apply rlimits, best-effort."""
    confine = _load_confine()
    try:
        os.chdir(tempfile.mkdtemp(prefix="airunner-math-"))
    except OSError:
        pass
    try:
        os.umask(0o077)
    except OSError:
        pass
    timeout = timeout_ms
    if not isinstance(timeout, int) or isinstance(timeout, bool):
        timeout = 10000
    return confine.apply_resource_limits(
        timeout,
        address_space_bytes=ADDRESS_SPACE_BYTES,
        max_processes=MAX_PROCESSES,
    )


def _run(code: str, namespace: dict[str, Any], stdout: Any) -> None:
    """Compile and exec one snippet with captured stdout."""
    from contextlib import redirect_stdout

    compiled = compile(code, "<math_executor>", "exec")
    with redirect_stdout(stdout):
        exec(compiled, namespace)


def worker_main() -> int:
    """Read one JSON request, write one framed JSON response."""
    try:
        raw = sys.stdin.buffer.read()
    except Exception as error:  # noqa: BLE001 - fail closed on bad stdin
        sys.stdout.write(json.dumps({"ok": False, "error": str(error)}))
        return 0
    try:
        if len(raw) > MAX_REQUEST_BYTES:
            raise ValueError("request exceeds the byte cap")
        request = json.loads(raw.decode("utf-8"))
        history = request.get("history", [])
        code = request.get("code", "")
        timeout_ms = request.get("timeout_ms", 10000)
        if not isinstance(history, list) or not all(
            isinstance(item, str) for item in history
        ):
            raise ValueError("history must be a list of strings")
        if not isinstance(code, str) or not code.strip():
            raise ValueError("missing code")
    except Exception as error:  # noqa: BLE001 - malformed request
        sys.stdout.write(
            json.dumps({"ok": False, "error": f"bad request: {error}"})
        )
        return 0
    limits = _isolate(timeout_ms)
    confine = _load_confine()
    namespace = _create_base_namespace()
    try:
        devnull: Any = confine.CappedWriter(0)
        for past in history:
            _run(past, namespace, devnull)
        captured = confine.CappedWriter(OUTPUT_CAP_BYTES)
        _run(code, namespace, captured)
    except SyntaxError as error:
        sys.stdout.write(
            json.dumps(
                {"ok": False, "error": f"Syntax error: {error}"}
            )
        )
        return 0
    except Exception as error:
        sys.stdout.write(
            json.dumps(
                {"ok": False, "error": f"Execution error: {error}"}
            )
        )
        return 0
    stdout_text = captured.text()
    if captured.overflow:
        sys.stdout.write(
            json.dumps(
                {
                    "ok": False,
                    "error": "Execution error: output exceeded "
                    "the byte cap",
                }
            )
        )
        return 0
    result = _json_safe(_extract_result(namespace, stdout_text))
    bindings = {
        name: _json_safe(namespace[name])
        for name in _top_level_names(code)
        if name in namespace
    }
    sys.stdout.write(
        json.dumps(
            {
                "ok": True,
                "result": result,
                "stdout": stdout_text,
                "error": "",
                "bindings": bindings,
                "pid": os.getpid(),
                "limits": limits,
            }
        )
    )
    return 0


if __name__ == "__main__":
    try:
        _exit_code = worker_main()
    except BaseException:  # noqa: BLE001 - last resort, fail closed
        traceback.print_exc()
        _exit_code = 3
    sys.exit(_exit_code)
