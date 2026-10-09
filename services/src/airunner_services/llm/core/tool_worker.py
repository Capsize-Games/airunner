"""Spawned custom-tool worker child (issue #2145, T01 section 3).

Runs ONE custom-tool invocation in a fresh interpreter started by
``tool_worker_runner`` as ``sys.executable <this file>``: never forked
(no GPU/Qt handle inheritance), never importing the service package.
Confinement comes from ``tool_worker_confine``; this module owns the
request loop, the restricted namespace and the single framed reply.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile
import traceback
from typing import Any

_SIBLINGS: dict[str, Any] = {}


def _load_sibling(name: str) -> Any:
    """Load one sibling module by path, cached (no package import)."""
    if name not in _SIBLINGS:
        import importlib.util

        here = os.path.dirname(os.path.abspath(__file__))
        path = os.path.join(here, name + ".py")
        spec = importlib.util.spec_from_file_location(f"w_{name}", path)
        if spec is None or spec.loader is None:
            raise ImportError(f"cannot load sibling {name}")
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        _SIBLINGS[name] = module
    return _SIBLINGS[name]


def _result(
    ipc: Any, status: str, error: str, token: str, **extra: Any
) -> dict[str, Any]:
    """Build one result dict with a bounded error string."""
    data = {
        "status": status,
        "value": None,
        "error": ipc.bounded_text(error),
        "truncated": False,
        "stdout": "",
        "cancel_token": token,
        "usage": {},
    }
    data.update(extra)
    return data


def _over_cap(ipc: Any, result_json: str) -> bool:
    """Return whether one serialized result exceeds the output cap."""
    return len(result_json.encode("utf-8")) > ipc.OUTPUT_CAP_BYTES


def _oversized_result(
    ipc: Any, result_json: str, stdout_text: str, token: str
) -> dict[str, Any]:
    """Build the bounded result for an over-cap output."""
    native = None if _over_cap(ipc, result_json) else json.loads(result_json)
    cut = stdout_text[: ipc.OUTPUT_CAP_BYTES]
    return _result(
        ipc,
        ipc.STATUS_OVERSIZED,
        "output exceeded the byte cap",
        token,
        value=native,
        stdout=cut,
        truncated=True,
    )


def _finish_ok(
    value: Any, captured: Any, token: str, ipc: Any
) -> dict[str, Any]:
    """Serialize one successful call, enforcing the output cap."""
    stdout_text = captured.text()
    try:
        result_json = ipc.dumps_jsonable(value)
    except (TypeError, ValueError) as error:
        detail = f"unserializable result: {error}"
        return _result(ipc, ipc.STATUS_TOOL_ERROR, detail, token)
    if captured.overflow or _over_cap(ipc, result_json):
        return _oversized_result(ipc, result_json, stdout_text, token)
    native = json.loads(result_json)
    return _result(
        ipc,
        ipc.STATUS_OK,
        "",
        token,
        value=native,
        stdout=stdout_text,
    )


def _exec_and_invoke(
    code: str,
    namespace: dict[str, Any],
    payload: dict[str, Any],
    confine: Any,
) -> Any:
    """Exec guarded code, find the tool, invoke it once."""
    exec(code, namespace)
    found = confine.find_tool(namespace, str(payload.get("tool_name", "")))
    return found(*payload.get("args", []), **payload.get("kwargs", {}))


def _canonical_roots(capabilities: Any) -> tuple[str, ...]:
    """Canonicalize granted roots; malformed input grants nothing."""
    if not isinstance(capabilities, dict):
        return ()
    raw = capabilities.get("fs_roots", [])
    if not isinstance(raw, (list, tuple)):
        return ()
    roots = [os.path.realpath(e) for e in raw if isinstance(e, str)]
    return tuple(r for r in roots if r)


def _prepared_call(
    payload: dict[str, Any], ipc: Any
) -> tuple[Any, dict[str, Any], Any]:
    """Load siblings; build the namespace plus capture buffer."""
    confine = _load_sibling("tool_worker_confine")
    sandbox = _load_sibling("code_sandbox")
    roots = _canonical_roots(payload.get("capabilities", {}))
    namespace = confine.build_namespace(sandbox.create_safe_builtins, roots)
    captured = confine.CappedWriter(ipc.OUTPUT_CAP_BYTES)
    return confine, namespace, captured


def _exec_and_call(
    payload: dict[str, Any], code: str, token: str, ipc: Any
) -> dict[str, Any]:
    """Exec guarded code in the namespace and call the tool."""
    confine, namespace, captured = _prepared_call(payload, ipc)
    saved_stdout, sys.stdout = sys.stdout, captured
    try:
        value = _exec_and_invoke(code, namespace, payload, confine)
    except confine.CapabilityDenied as denied:
        outcome = _result(
            ipc, ipc.STATUS_CAPABILITY_DENIED, str(denied), token
        )
    except Exception as error:
        traceback.print_exc()
        outcome = _result(
            ipc,
            ipc.STATUS_TOOL_ERROR,
            f"{type(error).__name__}: {error}",
            token,
        )
    else:
        outcome = _finish_ok(value, captured, token, ipc)
    finally:
        sys.stdout = saved_stdout
    return outcome


def execute_tool_request(payload: dict[str, Any], ipc: Any) -> dict[str, Any]:
    """Guard, exec and call one tool request in this process."""
    confine = _load_sibling("tool_worker_confine")
    token = str(payload.get("cancel_token", ""))
    code = payload.get("code", "")
    if not isinstance(code, str) or not code.strip():
        return _result(ipc, ipc.STATUS_TOOL_ERROR, "missing code", token)
    reason = confine.guard_tool_code(code)
    if reason is not None:
        return _result(ipc, ipc.STATUS_CAPABILITY_DENIED, reason, token)
    return _exec_and_call(payload, code, token, ipc)


def _verify_code_hash(payload: dict[str, Any]) -> None:
    """Refuse one request whose code mismatches the sha256 claim."""
    code = payload.get("code", "")
    want = payload.get("code_hash", "")
    if not isinstance(code, str):
        raise ValueError("code must be a string")
    digest = hashlib.sha256(code.encode("utf-8")).hexdigest()
    if not want or digest != want:
        raise ValueError("code_hash mismatch")


def _isolate_process(payload: dict[str, Any], ipc: Any) -> None:
    """Chdir to an empty temp dir and apply rlimits, best-effort."""
    confine = _load_sibling("tool_worker_confine")
    try:
        os.chdir(tempfile.mkdtemp(prefix="airunner-tool-"))
    except OSError:
        pass
    try:
        os.umask(0o077)
    except OSError:
        pass
    timeout = payload.get("timeout_ms", ipc.DEFAULT_TIMEOUT_MS)
    if not isinstance(timeout, int) or isinstance(timeout, bool):
        timeout = ipc.DEFAULT_TIMEOUT_MS
    confine.apply_resource_limits(timeout)


def _write_response(stream: Any, ipc: Any, result: dict[str, Any]) -> None:
    """Write one framed JSON response to the real stdout."""
    data = ipc.dumps_jsonable(result).encode("utf-8")
    stream.write(ipc.encode_frame(data))
    stream.flush()


def _read_request(ipc: Any, stdin: Any) -> dict[str, Any]:
    """Read, decode and hash-check one request from stdin."""
    raw = ipc.read_frame(stdin, ipc.MAX_REQUEST_BYTES)
    payload = ipc.loads_jsonable(raw.decode("utf-8"))
    _verify_code_hash(payload)
    return payload


def _request_error(ipc: Any, error: Exception) -> dict[str, Any]:
    """Build the error result for an unreadable request."""
    return _result(ipc, ipc.STATUS_TOOL_ERROR, f"bad request: {error}", "")


def worker_main() -> int:
    """Read one request from stdin, write one framed response."""
    ipc = _load_sibling("tool_worker_ipc")
    stdin = getattr(sys.stdin, "buffer", sys.stdin)
    stdout = getattr(sys.stdout, "buffer", sys.stdout)
    try:
        payload = _read_request(ipc, stdin)
    except Exception as error:
        _write_response(stdout, ipc, _request_error(ipc, error))
        return 0
    _isolate_process(payload, ipc)
    try:
        result = execute_tool_request(payload, ipc)
    except BaseException:
        return 3
    _write_response(stdout, ipc, result)
    return 0


if __name__ == "__main__":
    sys.exit(worker_main())
