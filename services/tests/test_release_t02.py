"""Custom-tool worker + ToolManager adapter tests (issue #2145, T02).

Behavior-neutral fixtures only; CPU-only; one loopback listener max.
"""

import importlib.util
import os
import signal
import socket
import sys
import threading
import time
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest import mock
import pytest

_CORE_DIR = (
    Path(__file__).resolve().parent.parent
    / "src"
    / "airunner_services"
    / "llm"
    / "core"
)
_ADD_CODE = (
    "@tool\n"
    "def add(a: int, b: int) -> int:\n"
    '    """Add two numbers."""\n'
    "    return a + b\n"
)
_LOOP_CODE = "@tool\ndef looper():\n    while True:\n        pass\n"


def _load_sibling(name: str) -> Any:
    """Load one stdlib-only core module by path (no pkg import)."""
    path = str(_CORE_DIR / (name + ".py"))
    spec = importlib.util.spec_from_file_location("t02_" + name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


_RUN = _load_sibling("tool_worker_runner")


try:
    from airunner_services.llm.tool_manager import ToolManager

    _NEEDS_MANAGER = pytest.mark.skipif(False, reason="stack present")
except ImportError:
    _NEEDS_MANAGER = pytest.mark.skipif(True, reason="needs llm stack")


def _no_zombie_children() -> None:
    """Fail if any worker child is still unreaped or running."""
    with pytest.raises(ChildProcessError):
        os.waitpid(-1, os.WNOHANG)


def _fake_record(**overrides: Any) -> SimpleNamespace:
    """Build a tool record double recording usage calls."""
    calls: list[tuple[bool, Any]] = []

    def increment_usage(success: bool = True, error: Any = None) -> None:
        calls.append((success, error))

    values = {
        "name": "demo",
        "code": _ADD_CODE,
        "safety_validated": True,
        "increment_usage": increment_usage,
    }
    values.update(overrides)
    record = SimpleNamespace(**values)
    record.usage_calls = calls
    return record


def test_benign_tool_round_trip() -> None:
    """A benign tool runs in the worker and returns its value."""
    out = _RUN.run_custom_tool(
        tool_name="add", code=_ADD_CODE, kwargs={"a": 40, "b": 2}
    )
    assert out.status == "ok"
    assert out.value == 42


def test_filesystem_escape_denied() -> None:
    """File access with no grant is denied without parent effects."""
    code = (
        "@tool\ndef grab() -> str:\n"
        "    return granted_read('/etc/hostname').decode()\n"
    )
    out = _RUN.run_custom_tool(tool_name="grab", code=code, kwargs={})
    assert out.status == "capability_denied"
    sneaky = "@tool\ndef grab():\n    return open('/tmp/x').read()\n"
    out = _RUN.run_custom_tool(tool_name="grab", code=sneaky, kwargs={})
    assert out.status == "capability_denied"


def test_network_egress_denied() -> None:
    """A socket attempt is denied; the listener sees no connection."""
    listener = socket.create_server(("127.0.0.1", 0), backlog=1)
    listener.settimeout(1)
    port = listener.getsockname()[1]
    code = (
        "@tool\ndef dial() -> str:\n    import socket\n"
        f"    socket.create_connection(('127.0.0.1', {port}))\n"
        "    return 'connected'\n"
    )
    try:
        out = _RUN.run_custom_tool(tool_name="dial", code=code, kwargs={})
        assert out.status == "capability_denied"
        with pytest.raises(socket.timeout):
            listener.accept()
    finally:
        listener.close()


@pytest.mark.parametrize(
    "code",
    [
        "@tool\ndef e():\n    import os\n",
        "@tool\ndef e():\n    return ().__class__.__base__\n",
        "@tool\ndef e():\n    return __import__('sys')\n",
    ],
)
def test_import_and_dunder_escape_denied(code: str) -> None:
    """Import and introspection escapes are denied pre-exec."""
    out = _RUN.run_custom_tool(tool_name="e", code=code, kwargs={})
    assert out.status == "capability_denied"


def test_timeout_reaps_worker() -> None:
    """An infinite loop times out; the worker is reaped."""
    start = time.monotonic()
    out = _RUN.run_custom_tool(
        tool_name="looper", code=_LOOP_CODE, kwargs={}, timeout_ms=1000
    )
    elapsed = time.monotonic() - start
    assert out.status == "timeout"
    assert elapsed < 10
    _no_zombie_children()


def test_output_bomb_is_bounded() -> None:
    """A 10 MB print becomes an oversized, bounded result."""
    code = (
        "@tool\ndef bomber():\n    for _ in range(10000):\n"
        "        print('x' * 1000)\n    return 'done'\n"
    )
    out = _RUN.run_custom_tool(tool_name="bomber", code=code, kwargs={})
    assert out.status == "oversized"
    assert out.truncated is True
    assert len(out.stdout.encode("utf-8")) <= 65536


def test_cancel_reaps_worker() -> None:
    """Cancel mid-run ends the worker and reports cancelled."""
    cancel = threading.Event()
    threading.Timer(0.3, cancel.set).start()
    out = _RUN.run_custom_tool(
        tool_name="looper",
        code=_LOOP_CODE,
        kwargs={},
        timeout_ms=10000,
        cancel_event=cancel,
    )
    assert out.status == "cancelled"
    _no_zombie_children()


def test_crash_maps_and_parent_healthy() -> None:
    """A killed worker maps to worker_crash; the parent survives."""
    out = _RUN.run_custom_tool(
        tool_name="add",
        code=_ADD_CODE,
        kwargs={"a": 1, "b": 2},
        spawn_hook=lambda pid: os.kill(pid, signal.SIGKILL),
    )
    assert out.status == "worker_crash"
    out = _RUN.run_custom_tool(
        tool_name="add", code=_ADD_CODE, kwargs={"a": 1, "b": 2}
    )
    assert (out.status, out.value) == ("ok", 3)


def test_grant_round_trips_bytes(tmp_path: Path) -> None:
    """Reads/writes inside a grant work exactly; outside is denied."""
    target = tmp_path / "blob.bin"
    code = (
        "@tool\ndef bridge(path: str) -> bytes:\n"
        "    granted_write(path, b'\\x00\\xffdata')\n"
        "    return granted_read(path)\n"
    )
    caps = _RUN.Capabilities(fs_roots=(str(tmp_path),))
    out = _RUN.run_custom_tool(
        tool_name="bridge",
        code=code,
        kwargs={"path": str(target)},
        capabilities=caps,
    )
    assert out.status == "ok"
    assert out.value == b"\x00\xffdata"
    out = _RUN.run_custom_tool(
        tool_name="bridge",
        code=code,
        kwargs={"path": "/tmp/t02-nope"},
        capabilities=caps,
    )
    assert out.status == "capability_denied"


def test_offline_blocks_network_grant(monkeypatch: Any) -> None:
    """A network grant while offline is blocked before any spawn."""
    pytest.importorskip("airunner_services.url_safety")
    from airunner_common import settings

    monkeypatch.setattr(settings, "AIRUNNER_OFFLINE_MODE", True)
    spawned: list[int] = []
    caps = _RUN.Capabilities(network=True)
    out = _RUN.run_custom_tool(
        tool_name="net",
        code=_ADD_CODE,
        capabilities=caps,
        spawn_hook=spawned.append,
    )
    assert out.status == "offline_blocked"
    assert spawned == []
    monkeypatch.setattr(settings, "AIRUNNER_OFFLINE_MODE", False)
    out = _RUN.run_custom_tool(
        tool_name="net",
        code=_ADD_CODE,
        capabilities=caps,
        spawn_hook=spawned.append,
    )
    assert out.status == "capability_denied"
    assert spawned == []


@_NEEDS_MANAGER
def test_adapter_preserves_tool_and_provenance() -> None:
    """Adapter keeps tools working and counts success/failure once."""
    manager = ToolManager(rag_manager=None)
    record = _fake_record()
    handle = manager._compile_custom_tool(record)
    assert handle is not None
    assert handle(40, 2) == 42
    assert record.usage_calls == [(True, None)]
    failing = _fake_record(
        code="@tool\ndef fail():\n    raise ValueError('x')\n"
    )
    handle = manager._compile_custom_tool(failing)
    assert handle is not None
    assert str(handle()).startswith("Error:")
    [(ok, message)] = failing.usage_calls
    assert ok is False and isinstance(message, str)


@_NEEDS_MANAGER
def test_adapter_timeout_is_bounded() -> None:
    """A hanging tool returns a bounded error, counted once."""
    manager = ToolManager(rag_manager=None)
    record = _fake_record(code=_LOOP_CODE, timeout_ms=1000)
    handle = manager._compile_custom_tool(record)
    assert handle is not None
    start = time.monotonic()
    assert str(handle()).startswith("Error:")
    assert time.monotonic() - start < 10
    [(ok, _message)] = record.usage_calls
    assert ok is False


@_NEEDS_MANAGER
def test_adapter_never_execs_in_parent() -> None:
    """Compiling and calling a tool never execs in this process."""
    manager = ToolManager(rag_manager=None)
    record = _fake_record()
    with mock.patch("builtins.exec", side_effect=AssertionError("exec")):
        handle = manager._compile_custom_tool(record)
        assert handle is not None
        assert handle(1, 2) == 3


@_NEEDS_MANAGER
def test_adapter_rejects_code_without_tool() -> None:
    """Code with no @tool function compiles to None (as before)."""
    manager = ToolManager(rag_manager=None)
    record = _fake_record(code="def plain():\n    return 1\n")
    assert manager._compile_custom_tool(record) is None
