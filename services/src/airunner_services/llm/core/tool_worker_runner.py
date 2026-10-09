"""Custom-tool worker supervisor (issue #2145): spawn-per-call parent.

Enforces timeout/cancel/caps/offline preflight; never execs tool bytes.
"""

from __future__ import annotations

import hashlib
import logging
import os
import struct
import subprocess
import sys
import time
from concurrent.futures import Future, ThreadPoolExecutor
from threading import Event
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


def _load_protocol() -> Any:
    """Load the stdlib-only protocol module by path (no pkg import)."""
    import importlib.util

    here = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(here, "tool_worker_ipc.py")
    spec = importlib.util.spec_from_file_location("tw_ipc", path)
    if spec is None or spec.loader is None:
        raise ImportError("cannot load tool_worker_ipc")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


_ipc = _load_protocol()
Capabilities = _ipc.Capabilities
normalize_timeout_ms = _ipc.normalize_timeout_ms
WorkerResult = _ipc.WorkerResult


class _RequestError(ValueError):
    """Rejects a request the worker must never see."""


def _res(
    status: str, error: str, usage: Any, truncated: bool = False
) -> WorkerResult:
    """Build one WorkerResult with the common fields."""
    return _ipc.WorkerResult(
        status=status, error=error, usage=usage, truncated=truncated
    )


def _check_network_grant(caps: Capabilities) -> Optional[WorkerResult]:
    """Apply the offline preflight; denying never spawns a worker."""
    if not caps.network:
        return None
    from airunner_services.url_safety import is_offline_mode

    if is_offline_mode():
        return _res(_ipc.STATUS_OFFLINE_BLOCKED, "offline: net denied", {})
    return _res(_ipc.STATUS_CAPABILITY_DENIED, "net grants denied", {})


def _serialize_arguments(args: Any, kwargs: Any) -> tuple[Any, Any]:
    """Round-trip call arguments; raise _RequestError if unusable."""
    try:
        args_json = _ipc.loads_jsonable(_ipc.dumps_jsonable(list(args)))
        kwargs_json = _ipc.loads_jsonable(_ipc.dumps_jsonable(dict(kwargs)))
    except (TypeError, ValueError) as error:
        raise _RequestError(f"arguments are not usable: {error}")
    return args_json, kwargs_json


def _build_payload(
    tool_name: str,
    code: str,
    args: Any,
    kwargs: Any,
    caps: Capabilities,
    timeout_ms: Any,
) -> tuple[bytes, str]:
    """Serialize one request frame; raise _RequestError, no spawn."""
    if not isinstance(code, str) or not code.strip():
        raise _RequestError("code must be a nonempty string")
    args_json, kwargs_json = _serialize_arguments(args, kwargs)
    timeout = normalize_timeout_ms(timeout_ms)
    payload = {
        "tool_name": tool_name,
        "code": code,
        "args": args_json,
        "kwargs": kwargs_json,
        "timeout_ms": timeout,
        "code_hash": hashlib.sha256(code.encode()).hexdigest(),
        "cancel_token": _ipc.new_cancel_token(),
        "capabilities": {"fs_roots": list(caps.fs_roots)},
    }
    data = _ipc.dumps_jsonable(payload).encode("utf-8")
    if len(data) > _ipc.MAX_REQUEST_BYTES:
        raise _RequestError("request exceeds the byte cap")
    return _ipc.encode_frame(data), payload["cancel_token"]


def _spawn_worker() -> subprocess.Popen[bytes]:
    """Spawn one fresh worker interpreter (never fork)."""
    here = os.path.dirname(os.path.abspath(__file__))
    worker = os.path.join(here, "tool_worker.py")
    return subprocess.Popen(
        [sys.executable, worker],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        close_fds=True,
    )


def _terminate(proc: subprocess.Popen[bytes]) -> None:
    """SIGTERM with a short grace, then SIGKILL; never raises."""
    try:
        proc.terminate()
        proc.wait(timeout=_ipc.TERMINATE_GRACE_SECONDS)
    except (OSError, subprocess.TimeoutExpired):
        pass
    if proc.poll() is None:
        try:
            proc.kill()
        except OSError:
            pass


def _supervise(
    future: Future[tuple[bytes, bytes]],
    proc: subprocess.Popen[bytes],
    timeout_s: float,
    cancel_event: Optional[Event],
) -> Optional[str]:
    """Poll for done/timeout/cancel; kill on timeout or cancel."""
    deadline = time.monotonic() + timeout_s
    while not future.done():
        if cancel_event is not None and cancel_event.is_set():
            _terminate(proc)
            return "cancelled"
        if time.monotonic() >= deadline:
            _terminate(proc)
            return "timeout"
        time.sleep(0.02)
    return None


def _await_completion(
    proc: subprocess.Popen[bytes],
    payload: bytes,
    timeout_s: float,
    cancel_event: Optional[Event],
) -> tuple[bytes, bytes, Optional[str]]:
    """Drain pipes in a thread; enforce wall timeout and cancel."""
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(proc.communicate, payload)
        outcome = _supervise(future, proc, timeout_s, cancel_event)
        stdout, stderr = future.result()
    return stdout, stderr, outcome


def _decode_frame(stdout: bytes) -> WorkerResult:
    """Decode one framed response or raise ValueError."""
    if len(stdout) < 4:
        raise ValueError("worker returned no response")
    (size,) = struct.unpack("!I", stdout[:4])
    if size > _ipc.MAX_RESPONSE_BYTES:
        return _res(_ipc.STATUS_OVERSIZED, "response over cap", {}, True)
    if len(stdout) - 4 < size:
        raise ValueError("worker response truncated")
    try:
        data = _ipc.loads_jsonable(stdout[4 : 4 + size].decode("utf-8"))
    except ValueError as error:
        raise ValueError(f"worker response is not JSON: {error}")
    return _ipc.WorkerResult.from_dict(data)


def _parse_response(
    returncode: int,
    stdout: bytes,
    token: str,
    wall_ms: int,
) -> WorkerResult:
    """Map worker exit/output to one WorkerResult (fail closed)."""
    usage = {"wall_ms": wall_ms}
    if returncode != 0:
        return _res(
            _ipc.STATUS_WORKER_CRASH, f"worker exit {returncode}", usage
        )
    try:
        result = _decode_frame(stdout)
    except ValueError as error:
        return _res(_ipc.STATUS_WORKER_CRASH, str(error), usage)
    if result.cancel_token and result.cancel_token != token:
        return _res(_ipc.STATUS_CANCELLED, "stale result", usage)
    result.usage["wall_ms"] = wall_ms
    return result


def _preflight(
    caps: Capabilities,
    cancel_event: Optional[Event],
) -> Optional[WorkerResult]:
    """Return an early result, or None when the worker may spawn."""
    if cancel_event is not None and cancel_event.is_set():
        return _res(_ipc.STATUS_CANCELLED, "cancelled before spawn", {})
    return _check_network_grant(caps)


def _collect_result(
    proc: subprocess.Popen[bytes],
    payload: bytes,
    token: str,
    timeout_ms: int,
    cancel_event: Optional[Event],
    start: float,
) -> WorkerResult:
    """Supervise one worker run and parse its single response."""
    stdout, stderr, outcome = _await_completion(
        proc, payload, timeout_ms / 1000.0, cancel_event
    )
    wall_ms = int((time.monotonic() - start) * 1000)
    if stderr:
        logger.debug(
            "tool worker stderr: %s", stderr.decode("utf-8", "replace")[:2000]
        )
    usage = {"wall_ms": wall_ms}
    if outcome == "cancelled":
        return _res(_ipc.STATUS_CANCELLED, "cancelled", usage)
    if outcome == "timeout":
        return _res(_ipc.STATUS_TIMEOUT, f"timeout {timeout_ms} ms", usage)
    return _parse_response(proc.returncode or 0, stdout, token, wall_ms)


def _spawn_and_wait(
    payload: bytes,
    token: str,
    timeout_ms: int,
    cancel_event: Optional[Event],
    spawn_hook: Optional[Callable[[int], None]],
) -> WorkerResult:
    """Spawn the worker and collect its single supervised result."""
    start = time.monotonic()
    try:
        proc = _spawn_worker()
    except OSError as error:
        return _res(_ipc.STATUS_WORKER_CRASH, f"spawn: {error}", {})
    if spawn_hook is not None:
        spawn_hook(proc.pid)
    return _collect_result(
        proc, payload, token, timeout_ms, cancel_event, start
    )


def run_custom_tool(
    *,
    tool_name: str,
    code: str,
    args: Any = (),
    kwargs: Any = None,
    capabilities: Optional[Capabilities] = None,
    timeout_ms: Any = None,
    cancel_event: Optional[Event] = None,
    spawn_hook: Optional[Callable[[int], None]] = None,
) -> WorkerResult:
    """Run one custom tool in a spawned worker; parent never execs."""
    caps = capabilities if capabilities is not None else Capabilities()
    denied = _preflight(caps, cancel_event)
    if denied is not None:
        return denied
    try:
        payload, token = _build_payload(
            tool_name, code, args, kwargs or {}, caps, timeout_ms
        )
    except _RequestError as error:
        return _res(_ipc.STATUS_TOOL_ERROR, str(error), {})
    timeout = normalize_timeout_ms(timeout_ms)
    return _spawn_and_wait(payload, token, timeout, cancel_event, spawn_hook)


__all__ = [
    "Capabilities",
    "normalize_timeout_ms",
    "run_custom_tool",
]
