"""Shared protocol for the custom-tool worker boundary (issue #2145).

Framed JSON messages plus the status vocabulary used by the parent
runner (``tool_worker_runner``) and the spawned child (``tool_worker``).
Stdlib-only: the child loads this file by path so it never imports the
service package (whose ``__init__`` chains pull the agent stack).
"""

from __future__ import annotations

import ast
import base64
import json
import struct
import uuid
from dataclasses import dataclass, field
from typing import Any, BinaryIO

STATUS_OK = "ok"
STATUS_TOOL_ERROR = "tool_error"
STATUS_TIMEOUT = "timeout"
STATUS_CANCELLED = "cancelled"
STATUS_CAPABILITY_DENIED = "capability_denied"
STATUS_WORKER_CRASH = "worker_crash"
STATUS_OVERSIZED = "oversized"
STATUS_OFFLINE_BLOCKED = "offline_blocked"

#: Default wall budget per custom-tool call (T01: default <= 10 s).
DEFAULT_TIMEOUT_MS = 10000
#: Captured-stdout and single-result cap enforced inside the worker.
OUTPUT_CAP_BYTES = 65536
#: Parent-side hard cap on one worker response frame.
MAX_RESPONSE_BYTES = 262144
#: Worker-side hard cap on one request frame (code + arguments).
MAX_REQUEST_BYTES = 1048576
#: Error strings shown to the model are cut to this many characters.
ERROR_PREVIEW_CHARS = 500
#: SIGTERM grace before the parent escalates to SIGKILL.
TERMINATE_GRACE_SECONDS = 0.5

_BYTES_MARKER = "__bytes_b64__"
_FRAME_HEADER = struct.Struct("!I")


def new_cancel_token() -> str:
    """Return one opaque token identifying a single worker run."""
    return uuid.uuid4().hex


def json_default(value: Any) -> Any:
    """Encode bytes and sets for a JSON result payload."""
    if isinstance(value, bytes):
        text = base64.b64encode(value).decode("ascii")
        return {_BYTES_MARKER: text}
    if isinstance(value, (set, frozenset, tuple)):
        return list(value)
    return str(value)


def json_object_hook(data: dict[str, Any]) -> Any:
    """Decode one ``json_default`` bytes marker back to bytes."""
    marker = data.get(_BYTES_MARKER)
    if set(data) == {_BYTES_MARKER} and isinstance(marker, str):
        return base64.b64decode(marker)
    return data


def dumps_jsonable(value: Any) -> str:
    """Serialize one value, encoding bytes via a marker dict."""
    return json.dumps(value, default=json_default)


def loads_jsonable(text: str) -> Any:
    """Parse one payload, decoding bytes markers back to bytes."""
    return json.loads(text, object_hook=json_object_hook)


def encode_frame(payload: bytes) -> bytes:
    """Prefix one payload with its 4-byte big-endian length."""
    return _FRAME_HEADER.pack(len(payload)) + payload


def read_exact(stream: BinaryIO, size: int) -> bytes:
    """Read exactly ``size`` bytes or raise EOFError."""
    chunks, remaining = [], size
    while remaining > 0:
        chunk = stream.read(remaining)
        if not chunk:
            raise EOFError(f"short read: {size - remaining}/{size}")
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)


def read_frame(stream: BinaryIO, max_bytes: int) -> bytes:
    """Read one length-prefixed frame, enforcing ``max_bytes``."""
    (size,) = _FRAME_HEADER.unpack(read_exact(stream, 4))
    if size > max_bytes:
        raise ValueError(f"frame of {size} bytes exceeds {max_bytes}")
    return read_exact(stream, size)


def bounded_text(text: str, limit: int = ERROR_PREVIEW_CHARS) -> str:
    """Truncate one error string, marking the truncation."""
    if len(text) <= limit:
        return text
    return text[:limit] + f"...[truncated {len(text) - limit} chars]"


@dataclass(frozen=True)
class Capabilities:
    """Per-call grants for one worker run; default denies all."""

    fs_roots: tuple[str, ...] = ()
    network: bool = False

    @classmethod
    def from_unknown(cls, value: Any) -> Capabilities:
        """Coerce a record field; anything malformed denies all."""
        if isinstance(value, Capabilities):
            return value
        if not isinstance(value, dict):
            return cls()
        raw = value.get("fs_roots", ())
        if not isinstance(raw, (list, tuple)):
            raw = ()
        roots = tuple(r for r in raw if isinstance(r, str) and r)
        return cls(fs_roots=roots, network=bool(value.get("network")))


def normalize_timeout_ms(value: Any) -> int:
    """Clamp a caller timeout to (0, DEFAULT]; garbage gets DEFAULT."""
    if isinstance(value, bool):
        return DEFAULT_TIMEOUT_MS
    try:
        timeout = int(value) if value is not None else DEFAULT_TIMEOUT_MS
    except (TypeError, ValueError):
        return DEFAULT_TIMEOUT_MS
    if timeout <= 0:
        return DEFAULT_TIMEOUT_MS
    return min(timeout, DEFAULT_TIMEOUT_MS)


@dataclass
class WorkerResult:
    """One worker outcome crossing the parent/child boundary."""

    status: str
    value: Any = None
    error: str = ""
    truncated: bool = False
    stdout: str = ""
    cancel_token: str = ""
    usage: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> WorkerResult:
        """Build one result, coercing a hostile or partial dict."""
        if not isinstance(data, dict):
            raise ValueError("result is not an object")
        get = data.get
        usage = get("usage", {})
        return cls(
            str(get("status", STATUS_WORKER_CRASH)),
            get("value"),
            str(get("error", "")),
            bool(get("truncated", False)),
            str(get("stdout", "")),
            str(get("cancel_token", "")),
            dict(usage) if isinstance(usage, dict) else {},
        )


def _tool_keywords(decorator: ast.AST) -> tuple[str, str, bool]:
    """Read @tool(...) overrides without executing code."""
    name, description, direct = "", "", False
    if not isinstance(decorator, ast.Call):
        return name, description, direct
    for arg in decorator.args[:1]:
        if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
            name = arg.value
    for keyword in decorator.keywords:
        value = keyword.value
        if not isinstance(value, ast.Constant):
            continue
        if keyword.arg == "name" and isinstance(value.value, str):
            name = value.value
        elif keyword.arg == "description" and isinstance(value.value, str):
            description = value.value
        elif keyword.arg == "return_direct":
            direct = bool(value.value)
    return name, description, direct


def _describe_function(node: ast.FunctionDef) -> tuple[str, str, bool] | None:
    """Describe one def if it carries the @tool decorator."""
    for decorator in node.decorator_list:
        target = decorator
        if isinstance(decorator, ast.Call):
            target = decorator.func
        if not (isinstance(target, ast.Name) and target.id == "tool"):
            continue
        name, description, direct = _tool_keywords(decorator)
        text = description or ast.get_docstring(node) or ""
        return name or node.name, text.strip(), direct
    return None


def describe_tool_code(code: str) -> tuple[str, str, bool] | None:
    """Describe the first @tool function without executing code."""
    try:
        tree = ast.parse(code)
    except (SyntaxError, ValueError):
        return None
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            meta = _describe_function(node)
            if meta is not None:
                return meta
    return None


__all__ = [
    "Capabilities",
    "DEFAULT_TIMEOUT_MS",
    "ERROR_PREVIEW_CHARS",
    "MAX_REQUEST_BYTES",
    "MAX_RESPONSE_BYTES",
    "OUTPUT_CAP_BYTES",
    "STATUS_CANCELLED",
    "STATUS_CAPABILITY_DENIED",
    "STATUS_OFFLINE_BLOCKED",
    "STATUS_OK",
    "STATUS_OVERSIZED",
    "STATUS_TIMEOUT",
    "STATUS_TOOL_ERROR",
    "STATUS_WORKER_CRASH",
    "TERMINATE_GRACE_SECONDS",
    "WorkerResult",
    "bounded_text",
    "describe_tool_code",
    "dumps_jsonable",
    "encode_frame",
    "json_default",
    "json_object_hook",
    "loads_jsonable",
    "new_cancel_token",
    "normalize_timeout_ms",
    "read_exact",
    "read_frame",
]
