"""Unit tests for the espeak render-process helpers.

_spawn_render_process and _await_render_process were extracted to
keep _run_bounded within the long-function threshold. These tests
pin the bounded wait checks: healthy exit, timeout, stalled reader,
overflow, read errors, and nonzero exit codes.
"""

import subprocess
import threading
from unittest.mock import MagicMock

import pytest

from airunner_services.runtimes.espeak_cli_renderer import (
    EspeakCliRenderer,
    EspeakRenderError,
)


def _make_renderer(popen=None):
    return EspeakCliRenderer.__new__(EspeakCliRenderer)


def _process(returncode=0):
    process = MagicMock()
    process.returncode = returncode
    return process


def _reader(alive=False):
    reader = MagicMock()
    reader.is_alive.return_value = alive
    return reader


def test_spawn_oserror_maps_to_backend_unavailable():
    renderer = _make_renderer()
    renderer._popen = MagicMock(side_effect=OSError("gone"))
    with pytest.raises(EspeakRenderError) as excinfo:
        renderer._spawn_render_process(["/usr/bin/espeak-ng"], b"")
    assert excinfo.value.code == "tts_backend_unavailable"


def test_spawn_invokes_popen_with_clean_env():
    renderer = _make_renderer()
    popen = MagicMock(return_value="proc")
    renderer._popen = popen
    assert renderer._spawn_render_process(["/usr/bin/espeak-ng"], b"abc") == "proc"
    _, kwargs = popen.call_args
    assert kwargs["shell"] is False
    assert kwargs["env"]["PATH"] == "/usr/bin:/bin"


def test_await_healthy_returns_joined_chunks():
    process = _process(0)
    out = EspeakCliRenderer._await_render_process(
        process, _reader(), [b"a", b"b"], threading.Event(), []
    )
    assert out == b"ab"


def test_await_timeout_kills_and_raises():
    process = _process(0)
    process.wait.side_effect = [
        subprocess.TimeoutExpired("x", 1),
        None,
    ]
    with pytest.raises(EspeakRenderError) as excinfo:
        EspeakCliRenderer._await_render_process(
            process, _reader(), [], threading.Event(), []
        )
    assert excinfo.value.code == "tts_timeout"
    process.kill.assert_called()


def test_await_stalled_reader_raises():
    process = _process(0)
    with pytest.raises(EspeakRenderError) as excinfo:
        EspeakCliRenderer._await_render_process(
            process, _reader(alive=True), [], threading.Event(), []
        )
    assert excinfo.value.code == "tts_render_failed"


def test_await_overflow_raises():
    process = _process(0)
    overflow = threading.Event()
    overflow.set()
    with pytest.raises(EspeakRenderError):
        EspeakCliRenderer._await_render_process(
            process, _reader(), [], overflow, []
        )


def test_await_read_error_chains_render_failed():
    process = _process(0)
    with pytest.raises(EspeakRenderError) as excinfo:
        EspeakCliRenderer._await_render_process(
            process, _reader(), [], threading.Event(), [OSError("io")]
        )
    assert excinfo.value.code == "tts_render_failed"


def test_await_nonzero_exit_raises():
    process = _process(3)
    with pytest.raises(EspeakRenderError):
        EspeakCliRenderer._await_render_process(
            process, _reader(), [], threading.Event(), []
        )
