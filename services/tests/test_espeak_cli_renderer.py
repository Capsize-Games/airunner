"""Fake-process coverage for the bounded eSpeak CLI renderer."""

from __future__ import annotations

import io
import os
import subprocess
import struct
import sys
import time
from types import SimpleNamespace

import pytest

from airunner_services.runtimes import espeak_cli_renderer as renderer_module
from airunner_services.runtimes.espeak_cli_renderer import (
    ESPEAK_EXECUTABLE,
    EspeakCliRenderer,
    EspeakRenderError,
)


VOICE_TABLE = b"""Pty Language Age/Gender VoiceName File Other Languages
 5 en-us --/M English_(America) gmw/en-US
 5 en-gb --/M English_(Britain) gmw/en
 5 fr --/M French roa/fr
 5 xx --/M MBROLA mb/mb-xx
 5 /etc/passwd --/M BadVoice /etc/passwd
"""
PCM_DATA = b"\x00\x00" * 64
WAV_STREAM = (
    b"RIFF"
    + struct.pack("<I", 0xFFFFFFFF)
    + b"WAVEfmt "
    + struct.pack("<IHHIIHH", 16, 1, 1, 22050, 44100, 2, 16)
    + b"data"
    + struct.pack("<I", 0xFFFFFFFF)
    + PCM_DATA
)
WAV_BYTES = bytearray(WAV_STREAM)
struct.pack_into("<I", WAV_BYTES, 4, len(WAV_BYTES) - 8)
struct.pack_into("<I", WAV_BYTES, 40, len(PCM_DATA))
WAV = bytes(WAV_BYTES)


class FakeProcess:
    def __init__(self, output: bytes, *, returncode: int = 0) -> None:
        self.stdin = io.BytesIO()
        self.stdout = io.BytesIO(output)
        self.returncode = returncode
        self.killed = False
        self.waited = False

    def wait(self, timeout=None):
        self.waited = True
        return self.returncode

    def poll(self):
        return self.returncode if self.waited or self.killed else None

    def kill(self):
        self.killed = True
        self.returncode = -9


class TimeoutProcess(FakeProcess):
    def wait(self, timeout=None):
        if timeout is not None:
            raise subprocess.TimeoutExpired("espeak-ng", timeout)
        self.waited = True
        return self.returncode


def _factory(outputs: list[bytes], calls: list[tuple[list[str], dict]]):
    def popen(argv, **kwargs):
        calls.append((argv, kwargs))
        return FakeProcess(outputs.pop(0))

    return popen


def test_renderer_uses_only_plain_text_cli_wav_and_actual_voice_ids() -> None:
    calls = []

    def popen(argv, **kwargs):
        stdin_text = kwargs["stdin"].read()
        kwargs["stdin"].seek(0)
        calls.append((argv, kwargs, stdin_text))
        output = VOICE_TABLE if argv[-1] == "--voices" else WAV_STREAM
        return FakeProcess(output)

    renderer = EspeakCliRenderer(
        popen=popen
    )

    result = renderer.render("hello", voice="en-us", speed=1.25)

    assert result == WAV
    assert renderer.voice_ids == ("en-gb", "en-us", "fr")
    argv = calls[1][0]
    assert argv == [
        ESPEAK_EXECUTABLE,
        "--stdout",
        "--stdin",
        "-v",
        "en-us",
        "-s",
        "125",
    ]
    assert "-m" not in argv
    assert calls[1][1]["shell"] is False
    assert calls[1][1]["stderr"] == subprocess.DEVNULL
    assert calls[1][1]["stdin"] != subprocess.PIPE
    assert calls[1][1]["cwd"] == "/"
    assert calls[1][2] == b"hello"
    assert struct.unpack_from("<I", result, 4)[0] == len(result) - 8
    assert struct.unpack_from("<I", result, 40)[0] == len(PCM_DATA)


@pytest.mark.parametrize(
    "text,voice,speed",
    [
        (" ", None, 1.0),
        ("hello\x00", None, 1.0),
        ("hello", "../../etc/passwd", 1.0),
        ("hello", "en-us", 0.25),
        ("hello", "en-us", float("inf")),
    ],
)
def test_renderer_rejects_invalid_request_without_spawn(text, voice, speed) -> None:
    calls = []
    renderer = EspeakCliRenderer(popen=_factory([], calls))

    with pytest.raises(EspeakRenderError):
        renderer.render(text, voice=voice, speed=speed)

    assert calls == []


def test_renderer_kills_and_reaps_process_when_output_exceeds_cap(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(renderer_module, "MAX_WAV_BYTES", 10)
    process = FakeProcess(b"x" * 1000)
    calls = []

    def popen(argv, **kwargs):
        calls.append((argv, kwargs))
        return process

    renderer = EspeakCliRenderer(popen=popen)
    renderer._voice_ids = ("en-us",)

    with pytest.raises(EspeakRenderError, match="exceeded the limit"):
        renderer.render("hello", voice="en-us", speed=1.0)

    assert process.killed
    assert process.waited


def test_renderer_kills_and_reaps_process_on_deadline() -> None:
    process = TimeoutProcess(b"")
    renderer = EspeakCliRenderer(
        popen=lambda *_args, **_kwargs: process
    )

    with pytest.raises(EspeakRenderError, match="timed out"):
        renderer.catalogue()

    assert process.killed
    assert process.waited


def test_deadline_with_maximum_multibyte_input_uses_owned_child_process(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(renderer_module, "PROCESS_TIMEOUT_SECONDS", 0.15)
    child_processes = []

    def popen(argv, **kwargs):
        if argv[-1] == "--voices":
            return FakeProcess(VOICE_TABLE)
        process = subprocess.Popen(
            [sys.executable, "-c", "import time; time.sleep(30)"],
            **kwargs,
        )
        child_processes.append(process)
        return process

    renderer = EspeakCliRenderer(popen=popen)
    started = time.monotonic()
    with pytest.raises(EspeakRenderError, match="timed out"):
        renderer.render("界" * 5000, voice="en-us", speed=1.0)
    elapsed = time.monotonic() - started

    assert elapsed < 2.0
    assert len(child_processes) == 1
    assert child_processes[0].poll() is not None
    assert child_processes[0].returncode == -9


def test_renderer_bounds_voice_catalogue_output(monkeypatch) -> None:
    monkeypatch.setattr(renderer_module, "MAX_CATALOG_BYTES", 8)
    process = FakeProcess(VOICE_TABLE)
    renderer = EspeakCliRenderer(
        popen=lambda *_args, **_kwargs: process
    )

    with pytest.raises(EspeakRenderError, match="exceeded the limit"):
        renderer.catalogue()

    assert process.killed
    assert process.waited


def test_renderer_rejects_invalid_wav_and_nonzero_exit() -> None:
    renderer = EspeakCliRenderer(
        popen=_factory([VOICE_TABLE, b"not-wav"], [])
    )
    with pytest.raises(EspeakRenderError, match="invalid WAV"):
        renderer.render("hello", voice="en-us", speed=1.0)

    renderer = EspeakCliRenderer(
        popen=lambda *_args, **_kwargs: FakeProcess(WAV, returncode=2)
    )
    renderer._voice_ids = ("en-us",)
    with pytest.raises(EspeakRenderError, match="process failed"):
        renderer.render("hello", voice="en-us", speed=1.0)


def test_eSpeak_selection_does_not_create_playback_worker(monkeypatch) -> None:
    from airunner_services.runtimes.contracts import RuntimeAction, RuntimeKind
    from airunner_services.ipc.messages import EnvelopeStatus, RequestEnvelope
    from airunner_services.runtimes.local_fallback import LocalFallbackTTSClient

    calls = []
    class LazyWorkerManager:
        @property
        def tts_generator_worker(self):
            raise AssertionError("worker accessed")

    worker_manager = LazyWorkerManager()
    client = LocalFallbackTTSClient(
        signal_source=SimpleNamespace(_worker_manager=worker_manager),
        mediator=SimpleNamespace(),
    )
    client._espeak_cli_renderer = EspeakCliRenderer(
        popen=_factory([VOICE_TABLE, WAV], calls)
    )
    monkeypatch.setenv("AIRUNNER_TTS_MODEL_TYPE", "Espeak")
    result = client.invoke(
        RequestEnvelope(
            request_id="espeak-cli",
            runtime=RuntimeKind.TTS,
            action=RuntimeAction.INVOKE,
            payload={"text": "hello", "voice": "en-us", "speed": 1.0},
        )
    )

    assert result.status is EnvelopeStatus.SUCCEEDED
    assert calls[1][0][0] == ESPEAK_EXECUTABLE
    health = client.healthcheck()
    assert health.metadata["model_id"] == "espeak-ng-cli"
    assert health.metadata["voice_ids"] == ["en-gb", "en-us", "fr"]
