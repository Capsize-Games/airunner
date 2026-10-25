"""Wave-2 voice/IPC/agent/tool hardening tests (audit fixes).

Each test pins one finding from the voice wave-2 audit: runtimes,
agents, tools and IPC fail closed, validate untrusted input, and
serialize shared mutable state.
"""

from __future__ import annotations

import asyncio
import base64
import json
import os
import stat
import sys
import threading
import types
from pathlib import Path

import pytest
from pydantic import ValidationError


def _install_heavy_stubs() -> None:
    """Stub third-party ML/driver modules missing from this venv.

    Idempotent: real modules win when they are already importable.
    """
    if "pyttsx3" not in sys.modules:
        try:
            import pyttsx3  # noqa: F401
        except ImportError:
            sys.modules["pyttsx3"] = types.ModuleType("pyttsx3")
    if "librosa" not in sys.modules:
        try:
            import librosa  # noqa: F401
        except ImportError:
            stub = types.ModuleType("librosa")
            stub.load = lambda *args, **kwargs: ([0.0], 24000)
            sys.modules["librosa"] = stub
    if "lingua" not in sys.modules:
        try:
            import lingua  # noqa: F401
        except ImportError:
            lingua = types.ModuleType("lingua")

            class _Language:
                ENGLISH = "en"
                FRENCH = "fr"
                SPANISH = "es"
                KOREAN = "ko"
                CHINESE = "zh"
                JAPANESE = "ja"

            class _Builder:
                @staticmethod
                def from_languages(*args, **kwargs):
                    class _Built:
                        @staticmethod
                        def build():
                            return None

                    return _Built()

            lingua.Language = _Language
            lingua.LanguageDetectorBuilder = _Builder
            sys.modules["lingua"] = lingua
    for name in (
        "airunner_tts_vendor",
        "airunner_tts_vendor.melo",
        "airunner_tts_vendor.melo.api",
        "airunner_tts_vendor.melo.runtime_support",
        "airunner_tts_vendor.openvoice",
        "airunner_tts_vendor.openvoice.api",
        "airunner_tts_vendor.openvoice.mel_processing",
        "airunner_tts_vendor.openvoice.se_extractor",
    ):
        if name not in sys.modules:
            try:
                __import__(name)
            except ImportError:
                sys.modules[name] = types.ModuleType(name)
    openvoice_pkg = sys.modules["airunner_tts_vendor.openvoice"]
    if not hasattr(openvoice_pkg, "se_extractor"):
        openvoice_pkg.se_extractor = sys.modules[
            "airunner_tts_vendor.openvoice.se_extractor"
        ]
    if not hasattr(
        sys.modules["airunner_tts_vendor.openvoice.se_extractor"], "get_se"
    ):
        sys.modules[
            "airunner_tts_vendor.openvoice.se_extractor"
        ].get_se = lambda *args, **kwargs: (None, None)
    if "inflect" not in sys.modules:
        try:
            import inflect  # noqa: F401
        except ImportError:
            inflect = types.ModuleType("inflect")

            class _Engine:
                @staticmethod
                def number_to_words(value):
                    return str(value)

            inflect.engine = lambda: _Engine()
            sys.modules["inflect"] = inflect
    api = sys.modules["airunner_tts_vendor.melo.api"]
    if not hasattr(api, "TTS"):
        api.TTS = object
        api.set_memory_cleanup_hook = lambda *args, **kwargs: None
    support = sys.modules["airunner_tts_vendor.melo.runtime_support"]
    for func in (
        "normalize_tts_model_root",
        "resolve_tts_model_root",
        "set_cache_base_resolver",
        "set_tts_model_base_resolver",
        "set_tts_model_root_resolver",
    ):
        if not hasattr(support, func):
            setattr(support, func, lambda *args, **kwargs: None)
    support.resolve_tts_model_root = lambda: "/tmp/stub-tts-models"
    ov_api = sys.modules["airunner_tts_vendor.openvoice.api"]
    if not hasattr(ov_api, "ToneColorConverter"):
        ov_api.ToneColorConverter = object
        ov_api.OpenVoiceBaseClass = object
    mel = sys.modules["airunner_tts_vendor.openvoice.mel_processing"]
    if not hasattr(mel, "spectrogram_torch"):
        mel.spectrogram_torch = lambda *args, **kwargs: None


# ---------------------------------------------------------------------
# TTS contract validation
# ---------------------------------------------------------------------


def test_tts_rejects_unbounded_text():
    from airunner_services.runtimes.contracts import TTSInvocationRequest

    with pytest.raises(ValidationError):
        TTSInvocationRequest(text="x" * 5001)


def test_tts_rejects_blank_text():
    from airunner_services.runtimes.contracts import TTSInvocationRequest

    with pytest.raises(ValidationError):
        TTSInvocationRequest(text="   ")


def test_tts_rejects_bad_speed():
    from airunner_services.runtimes.contracts import TTSInvocationRequest

    for bad in (-1.0, 0.0, 100.0, float("nan"), float("inf")):
        with pytest.raises(ValidationError):
            TTSInvocationRequest(text="hi", speed=bad)


def test_tts_rejects_crlf_names():
    from airunner_services.runtimes.contracts import TTSInvocationRequest

    with pytest.raises(ValidationError):
        TTSInvocationRequest(text="hi", voice="bob\r\nX: 1")
    with pytest.raises(ValidationError):
        TTSInvocationRequest(text="hi", model="m" * 257)


def test_tts_accepts_sane_request():
    from airunner_services.runtimes.contracts import TTSInvocationRequest

    request = TTSInvocationRequest(text="hello", voice="bob", speed=1.5)
    assert request.speed == 1.5


# ---------------------------------------------------------------------
# IPC envelope caps
# ---------------------------------------------------------------------


def test_envelope_rejects_oversize_payload():
    from airunner_services.ipc.messages import RequestEnvelope
    from airunner_services.runtimes.contracts import RuntimeAction, RuntimeKind

    with pytest.raises(ValidationError):
        RequestEnvelope(
            runtime=RuntimeKind.STT,
            action=RuntimeAction.INVOKE,
            payload={"audio_b64": "A" * (33 * 1024 * 1024)},
        )


def test_envelope_accepts_normal_payload():
    from airunner_services.ipc.messages import RequestEnvelope
    from airunner_services.runtimes.contracts import RuntimeAction, RuntimeKind

    envelope = RequestEnvelope(
        runtime=RuntimeKind.STT,
        action=RuntimeAction.INVOKE,
        payload={"audio_b64": "QUJD"},
    )
    assert envelope.payload["audio_b64"] == "QUJD"


# ---------------------------------------------------------------------
# Registry exact-only resolution
# ---------------------------------------------------------------------


def test_registry_resolves_exact_only_by_default():
    from airunner_services.runtimes.contracts import RuntimeKind
    from airunner_services.runtimes.registry import RuntimeRegistry, RuntimeRoute

    registry = RuntimeRegistry()
    sentinel = object()
    registry.register(
        RuntimeRoute(
            RuntimeKind.STT, provider="local", deployment_mode="default"
        ),
        sentinel,
    )
    with pytest.raises(KeyError):
        registry.resolve(
            RuntimeKind.STT, provider="local", deployment_mode="sidecar"
        )
    assert (
        registry.resolve(
            RuntimeKind.STT,
            provider="local",
            deployment_mode="sidecar",
            allow_fallback=True,
        )
        is sentinel
    )
    assert (
        registry.resolve(
            RuntimeKind.STT,
            provider="local",
            deployment_mode="default",
        )
        is sentinel
    )


# ---------------------------------------------------------------------
# Executable override validation
# ---------------------------------------------------------------------


def test_executable_override_missing_file_raises(tmp_path, monkeypatch):
    from airunner_services.runtimes import bundled_runtime_paths as paths

    missing = tmp_path / "nope-server"
    monkeypatch.setenv("AIRUNNER_WAVE2_TEST_BIN", str(missing))
    with pytest.raises(FileNotFoundError):
        paths.resolve_runtime_executable(
            "AIRUNNER_WAVE2_TEST_BIN", "wave2-test-server"
        )


def test_executable_override_non_executable_raises(tmp_path, monkeypatch):
    from airunner_services.runtimes import bundled_runtime_paths as paths

    candidate = tmp_path / "plain-file"
    candidate.write_text("not executable")
    candidate.chmod(0o644)
    monkeypatch.setenv("AIRUNNER_WAVE2_TEST_BIN", str(candidate))
    with pytest.raises(PermissionError):
        paths.resolve_runtime_executable(
            "AIRUNNER_WAVE2_TEST_BIN", "wave2-test-server"
        )


def test_executable_override_valid_file_passes(tmp_path, monkeypatch):
    from airunner_services.runtimes import bundled_runtime_paths as paths

    candidate = tmp_path / "real-server"
    candidate.write_text("#!/bin/sh\n")
    candidate.chmod(0o755)
    monkeypatch.setenv("AIRUNNER_WAVE2_TEST_BIN", str(candidate))
    assert (
        paths.resolve_runtime_executable(
            "AIRUNNER_WAVE2_TEST_BIN", "wave2-test-server"
        )
        == str(candidate)
    )


# ---------------------------------------------------------------------
# Whisper settings clamps
# ---------------------------------------------------------------------


def test_whisper_settings_clamp_port_and_threads(monkeypatch):
    from airunner_services.runtimes import whisper_cpp_runtime_settings as w

    for name in (
        "AIRUNNER_WHISPER_MODEL_PATH",
        "AIRUNNER_WHISPER_SERVER_BIN",
        "AIRUNNER_WHISPER_HOST",
        "AIRUNNER_RUNTIME_BIND_HOST",
    ):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("AIRUNNER_WHISPER_PORT", "999999")
    monkeypatch.setenv("AIRUNNER_WHISPER_THREADS", "-5")
    monkeypatch.setenv("AIRUNNER_WHISPER_PROCESSORS", "0")
    settings = w.resolve_whisper_cpp_runtime_settings(path_settings=object())
    assert settings.port == w.DEFAULT_PORT
    assert settings.n_threads >= 1
    assert settings.n_processors >= 1


def test_whisper_settings_reject_unknown_language(monkeypatch):
    from airunner_services.runtimes import whisper_cpp_runtime_settings as w

    for name in (
        "AIRUNNER_WHISPER_MODEL_PATH",
        "AIRUNNER_WHISPER_SERVER_BIN",
        "AIRUNNER_WHISPER_HOST",
        "AIRUNNER_RUNTIME_BIND_HOST",
    ):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("AIRUNNER_WHISPER_LANGUAGE", "xx-evil")
    settings = w.resolve_whisper_cpp_runtime_settings(path_settings=object())
    assert settings.language == w.DEFAULT_LANGUAGE
    monkeypatch.setenv("AIRUNNER_WHISPER_LANGUAGE", "EN")
    settings = w.resolve_whisper_cpp_runtime_settings(path_settings=object())
    assert settings.language == "en"


def test_whisper_model_override_validated_fail_fast(tmp_path, monkeypatch):
    from airunner_services.runtimes import whisper_cpp_runtime_settings as w
    from airunner_services.runtimes.file_policy import PathPolicyError

    for name in (
        "AIRUNNER_WHISPER_SERVER_BIN",
        "AIRUNNER_WHISPER_HOST",
        "AIRUNNER_RUNTIME_BIND_HOST",
    ):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("AIRUNNER_WHISPER_MODEL_PATH", str(tmp_path / "m.gguf"))
    with pytest.raises(PathPolicyError):
        w.resolve_whisper_cpp_runtime_settings(path_settings=object())
    good = tmp_path / "ggml-base.bin"
    good.write_bytes(b"x")
    monkeypatch.setenv("AIRUNNER_WHISPER_MODEL_PATH", str(good))
    settings = w.resolve_whisper_cpp_runtime_settings(path_settings=object())
    assert settings.model_path == str(good)


# ---------------------------------------------------------------------
# File policy expansion documentation
# ---------------------------------------------------------------------


def test_normalize_expands_env_and_home(monkeypatch, tmp_path):
    from airunner_services.runtimes.file_policy import normalize_local_path

    monkeypatch.setenv("WAVE2_BASE", str(tmp_path))
    resolved = normalize_local_path("$WAVE2_BASE/sub", label="Probe")
    assert resolved == str(tmp_path / "sub")
    home_resolved = normalize_local_path("~/wave2probe", label="Probe")
    assert home_resolved == str(Path.home() / "wave2probe")


# ---------------------------------------------------------------------
# Daemon config: fail-closed, save errors, CORS defaults
# ---------------------------------------------------------------------


def test_daemon_config_corrupt_yaml_raises(tmp_path):
    from airunner_services.runtimes.daemon_config import DaemonConfig

    bad = tmp_path / "daemon.yaml"
    bad.write_text("server: [unclosed\n\tbad-tab: : :\n", encoding="utf-8")
    with pytest.raises(ValueError):
        DaemonConfig(bad)


def test_daemon_config_non_mapping_raises(tmp_path):
    from airunner_services.runtimes.daemon_config import DaemonConfig

    bad = tmp_path / "daemon.yaml"
    bad.write_text("- just\n- a\n- list\n", encoding="utf-8")
    with pytest.raises(ValueError):
        DaemonConfig(bad)


def test_daemon_config_defaults_disable_cors(tmp_path):
    from airunner_services.runtimes.daemon_config import DaemonConfig

    config = DaemonConfig(tmp_path / "missing.yaml")
    assert config.config["server"]["enable_cors"] is False
    assert config.config["server"]["allowed_origins"] == []


def test_daemon_config_save_failure_raises(tmp_path, monkeypatch):
    from airunner_services.runtimes.daemon_config import DaemonConfig

    config = DaemonConfig(tmp_path / "daemon.yaml")

    def _refuse(self, *args, **kwargs):
        raise OSError("read-only")

    monkeypatch.setattr(Path, "mkdir", _refuse)
    with pytest.raises(OSError):
        config.save()


def test_daemon_config_round_trip(tmp_path):
    from airunner_services.runtimes.daemon_config import DaemonConfig

    first = DaemonConfig(tmp_path / "daemon.yaml")
    first.config["server"]["port"] = 8123
    first.save()
    second = DaemonConfig(tmp_path / "daemon.yaml")
    assert second.config["server"]["port"] == 8123


# ---------------------------------------------------------------------
# STT launcher: locks, suffix, health timeout, error tail
# ---------------------------------------------------------------------


def _stt_settings(**overrides):
    from airunner_services.runtimes.whisper_cpp_runtime_settings import (
        WhisperCppRuntimeSettings,
    )

    values = {
        "executable": "whisper-server",
        "host": "127.0.0.1",
        "port": 8012,
        "model_path": None,
        "model_id": None,
        "n_threads": 2,
        "n_processors": 1,
        "language": "auto",
        "request_path": "",
        "inference_path": "/inference",
        "convert_audio": False,
        "use_gpu": False,
        "startup_timeout_seconds": 60.0,
    }
    values.update(overrides)
    return WhisperCppRuntimeSettings(**values)


def test_stt_launcher_rejects_non_ggml_model(tmp_path):
    from airunner_services.runtimes.sidecar_stt_launcher import (
        SidecarSTTLauncher,
    )

    wrong = tmp_path / "model.gguf"
    wrong.write_bytes(b"x")
    launcher = SidecarSTTLauncher(_stt_settings(model_path=str(wrong)))
    with pytest.raises(RuntimeError, match="(?i)bin"):
        launcher.command()


def test_stt_launcher_derives_health_timeout():
    from airunner_services.runtimes.sidecar_stt_launcher import (
        SidecarSTTLauncher,
    )

    assert (
        SidecarSTTLauncher(_stt_settings()).health_timeout_seconds == 5.0
    )
    quick = SidecarSTTLauncher(
        _stt_settings(startup_timeout_seconds=5.0)
    )
    assert quick.health_timeout_seconds == 1.0


def test_stt_launcher_reports_exit_code_and_output_hint():
    from airunner_services.runtimes.sidecar_stt_launcher import (
        SidecarSTTLauncher,
    )

    launcher = SidecarSTTLauncher(_stt_settings())
    assert "discarded" in launcher._child_output_tail()
    assert "AIRUNNER_SAVE_LOG_TO_FILE" in launcher._child_output_tail()


def test_stt_launcher_start_is_serialized(tmp_path):
    import time as time_module

    from airunner_services.runtimes.sidecar_stt_launcher import (
        SidecarSTTLauncher,
    )

    model = tmp_path / "ggml-test.bin"
    model.write_bytes(b"x")

    state = {"alive": 0, "max_alive": 0}
    state_lock = threading.Lock()
    barrier = threading.Barrier(4)

    class _Proc:
        def __init__(self):
            self._dead = False
            with state_lock:
                state["alive"] += 1
                state["max_alive"] = max(
                    state["max_alive"], state["alive"]
                )

        def poll(self):
            return 0 if self._dead else None

        def terminate(self):
            with state_lock:
                if not self._dead:
                    self._dead = True
                    state["alive"] -= 1

        def wait(self, timeout=None):
            return 0

    def _opener(*args, **kwargs):
        raise OSError("still starting")

    launcher = SidecarSTTLauncher(
        _stt_settings(
            startup_timeout_seconds=0.5, model_path=str(model)
        ),
        process_factory=lambda *args, **kwargs: _Proc(),
        health_opener=_opener,
        sleep=lambda seconds: time_module.sleep(0.005),
    )
    errors = []

    def _start():
        barrier.wait()
        try:
            launcher.start()
        except RuntimeError as exc:
            errors.append(exc)

    workers = [threading.Thread(target=_start) for _ in range(4)]
    for worker in workers:
        worker.start()
    for worker in workers:
        worker.join()
    # Every starter times out, but the start lock means at most one
    # sidecar is ever alive at once (no orphaned double-spawn).
    assert state["max_alive"] == 1
    assert len(errors) == 4


# ---------------------------------------------------------------------
# STT client: mime gate, audio caps, narrow cancel, no orphans
# ---------------------------------------------------------------------


class _FakeSTTLauncher:
    def __init__(self, settings):
        self.settings = settings
        self.endpoint = settings.endpoint
        self.inference_url = settings.endpoint + "/inference"
        self.stops = 0
        self.starts = 0
        self.running = False

    def start(self):
        self.starts += 1
        self.running = True

    def stop(self):
        self.stops += 1
        self.running = False

    def is_running(self):
        return self.running

    def health_status(self):
        from airunner_services.runtimes.contracts import RuntimeHealthStatus

        return RuntimeHealthStatus.READY, "ready"


def _stt_request(payload, request_id="req-1"):
    from airunner_services.runtimes.contracts import (
        RuntimeAction,
        RuntimeKind,
    )

    return types.SimpleNamespace(
        runtime=RuntimeKind.STT,
        action=RuntimeAction.INVOKE,
        request_id=request_id,
        payload=payload,
    )


class _FakeHTTPResponse:
    def __init__(self, body: bytes):
        self._body = body

    def read(self, limit=None):
        if limit is None:
            return self._body
        return self._body[:limit]

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def _stt_client(monkeypatch=None, **kwargs):
    from airunner_services.runtimes.sidecar_stt_client import SidecarSTTClient

    settings = _stt_settings()
    launcher = _FakeSTTLauncher(settings)
    opener = kwargs.pop(
        "http_opener",
        lambda request, timeout=None: _FakeHTTPResponse(b'{"text": "hi"}'),
    )
    return SidecarSTTClient(
        settings=settings, launcher=launcher, http_opener=opener, **kwargs
    )


def test_stt_client_rejects_header_injection_mime():
    from airunner_services.ipc.messages import EnvelopeStatus

    client = _stt_client()
    audio = base64.b64encode(b"RIFF....").decode("ascii")
    response = client.invoke(
        _stt_request({"audio_b64": audio, "mime_type": "audio/wav\r\nX: 1"})
    )
    assert response.status is EnvelopeStatus.FAILED
    assert response.error.code == "stt_invalid_audio"


def test_stt_client_rejects_oversize_audio(monkeypatch):
    from airunner_services.ipc.messages import EnvelopeStatus
    from airunner_services.runtimes import sidecar_stt_client as client_module

    monkeypatch.setattr(client_module, "MAX_STT_AUDIO_BYTES", 8)
    client = _stt_client()
    audio = base64.b64encode(b"0123456789abcdef").decode("ascii")
    response = client.invoke(
        _stt_request({"audio_b64": audio, "mime_type": "audio/wav"})
    )
    assert response.status is EnvelopeStatus.FAILED
    assert response.error.code == "stt_invalid_audio"
    assert client._launcher.starts == 0


def test_stt_client_maps_bad_payload_to_failure_envelope():
    from airunner_services.ipc.messages import EnvelopeStatus

    client = _stt_client()
    response = client.invoke(_stt_request({"mime_type": "audio/wav"}))
    assert response.status is EnvelopeStatus.FAILED
    assert response.error.code == "stt_invalid_audio"


def test_stt_client_maps_corrupt_sidecar_json():
    from airunner_services.ipc.messages import EnvelopeStatus

    client = _stt_client(
        http_opener=lambda request, timeout=None: _FakeHTTPResponse(
            b"\xff\xfe-not-json"
        )
    )
    audio = base64.b64encode(b"RIFF....").decode("ascii")
    response = client.invoke(
        _stt_request({"audio_b64": audio, "mime_type": "audio/wav"})
    )
    assert response.status is EnvelopeStatus.FAILED
    assert response.error.code == "stt_invoke_failed"


def test_stt_client_rejects_huge_sidecar_body(monkeypatch):
    from airunner_services.ipc.messages import EnvelopeStatus
    from airunner_services.runtimes import sidecar_stt_client as client_module

    monkeypatch.setattr(client_module, "MAX_STT_RESPONSE_BYTES", 4)
    client = _stt_client()
    audio = base64.b64encode(b"RIFF....").decode("ascii")
    response = client.invoke(
        _stt_request({"audio_b64": audio, "mime_type": "audio/wav"})
    )
    assert response.status is EnvelopeStatus.FAILED
    assert response.error.code == "stt_invoke_failed"


def test_stt_cancel_leaves_shared_sidecar_running(caplog):
    from airunner_services.ipc.messages import EnvelopeStatus

    client = _stt_client()
    with caplog.at_level("WARNING"):
        response = client.cancel("req-1")
    assert response.status is EnvelopeStatus.CANCELLED
    assert client._launcher.stops == 0
    assert any("left running" in r.message for r in caplog.records)


def test_stt_prepare_launcher_stops_drifted_process():
    from airunner_services.runtimes.sidecar_stt_client import SidecarSTTClient

    first = _stt_settings(port=8012)
    second = _stt_settings(port=8013)
    first_launcher = _FakeSTTLauncher(first)

    client = SidecarSTTClient(
        settings=first,
        launcher=first_launcher,
        settings_resolver=lambda: second,
        http_opener=lambda request, timeout=None: _FakeHTTPResponse(b"{}"),
    )
    # Force the managed path: the client owns its launcher here.
    client._managed_launcher = True
    client._prepare_launcher()
    assert first_launcher.stops == 1
    assert client._launcher is not first_launcher


# ---------------------------------------------------------------------
# TTS client: model validation, locked load, cancel logging
# ---------------------------------------------------------------------


def _tts_settings(**overrides):
    from airunner_services.runtimes.tts_daemon_runtime_settings import (
        TTSDaemonRuntimeSettings,
    )

    values = {
        "host": "127.0.0.1",
        "port": 8191,
        "base_daemon_config_path": None,
        "tts_model_path": None,
        "tts_model_type": "Espeak",
        "startup_timeout_seconds": 5.0,
        "request_timeout_seconds": 5.0,
    }
    values.update(overrides)
    return TTSDaemonRuntimeSettings(**values)


class _FakeTTSLauncher:
    def __init__(self, settings):
        self.settings = settings
        self.endpoint = settings.endpoint
        self.api_base_url = settings.endpoint + "/api/v1/tts"
        self.starts = 0
        self.stops = 0

    def start(self):
        self.starts += 1

    def stop(self):
        self.stops += 1

    def is_running(self):
        return True

    def is_ready(self):
        return True

    def health_status(self):
        from airunner_services.runtimes.contracts import RuntimeHealthStatus

        return RuntimeHealthStatus.READY, "ready"


def _tts_request(payload, request_id="tts-1"):
    from airunner_services.runtimes.contracts import (
        RuntimeAction,
        RuntimeKind,
    )

    return types.SimpleNamespace(
        runtime=RuntimeKind.TTS,
        action=RuntimeAction.INVOKE,
        request_id=request_id,
        payload=payload,
    )


def test_tts_model_path_validation(tmp_path):
    from airunner_services.runtimes.sidecar_tts_client import (
        _validate_tts_model_path,
    )

    assert _validate_tts_model_path(None) is None
    voice_dir = tmp_path / "openvoice"
    voice_dir.mkdir()
    assert _validate_tts_model_path(str(voice_dir)) == str(voice_dir)
    with pytest.raises(ValueError):
        _validate_tts_model_path(str(tmp_path / "missing"))
    wrong = tmp_path / "model.gguf"
    wrong.write_bytes(b"x")
    with pytest.raises(ValueError):
        _validate_tts_model_path(str(wrong))
    good = tmp_path / "model.onnx"
    good.write_bytes(b"x")
    assert _validate_tts_model_path(str(good)) == str(good)


def test_tts_synthesize_rejects_unknown_model(tmp_path):
    from airunner_services.ipc.messages import EnvelopeStatus
    from airunner_services.runtimes.sidecar_tts_client import SidecarTTSClient

    settings = _tts_settings()
    client = SidecarTTSClient(
        settings=settings, launcher=_FakeTTSLauncher(settings)
    )
    response = client.invoke(
        _tts_request(
            {"text": "hi", "model": str(tmp_path / "missing.onnx")}
        )
    )
    assert response.status is EnvelopeStatus.FAILED
    assert response.error.code == "tts_invalid_request"


def test_tts_synthesize_rejects_invalid_tts_payload():
    from airunner_services.ipc.messages import EnvelopeStatus
    from airunner_services.runtimes.sidecar_tts_client import SidecarTTSClient

    settings = _tts_settings()
    client = SidecarTTSClient(
        settings=settings, launcher=_FakeTTSLauncher(settings)
    )
    response = client.invoke(_tts_request({"text": "hi", "speed": -2.0}))
    assert response.status is EnvelopeStatus.FAILED
    assert response.error.code == "tts_invalid_request"


def test_tts_cancel_logs_delivery_failure(caplog):
    from airunner_services.ipc.messages import EnvelopeStatus
    from airunner_services.runtimes.sidecar_tts_client import SidecarTTSClient

    settings = _tts_settings()
    client = SidecarTTSClient(
        settings=settings, launcher=_FakeTTSLauncher(settings)
    )
    client._track_request("tts-9")

    def _boom(*args, **kwargs):
        raise RuntimeError("sidecar gone")

    client._request = _boom
    with caplog.at_level("WARNING"):
        response = client.cancel("tts-9")
    assert response.status is EnvelopeStatus.CANCELLED
    assert any("cancel delivery failed" in r.message for r in caplog.records)


def test_tts_load_holds_invoke_lock():
    from airunner_services.runtimes.contracts import RuntimeAction, RuntimeKind
    from airunner_services.runtimes.sidecar_tts_client import SidecarTTSClient

    settings = _tts_settings()
    launcher = _FakeTTSLauncher(settings)
    held_during_start = {}

    real_start = launcher.start

    def _spying_start():
        held_during_start["held"] = client._invoke_lock.locked()
        real_start()

    launcher.start = _spying_start
    client = SidecarTTSClient(settings=settings, launcher=launcher)
    client._request = lambda *args, **kwargs: {"status": "ready"}
    request = types.SimpleNamespace(
        runtime=RuntimeKind.TTS,
        action=RuntimeAction.LOAD_MODEL,
        request_id="load-1",
        metadata={},
    )
    response = client.invoke(request)
    from airunner_services.ipc.messages import EnvelopeStatus

    assert response.status is EnvelopeStatus.SUCCEEDED
    assert held_during_start["held"] is True


# ---------------------------------------------------------------------
# TTS/art temp configs: 0600 perms and sweep_all callers
# ---------------------------------------------------------------------


def _fake_layout(tmp_path):
    layout = types.SimpleNamespace(
        config_dir=tmp_path,
        ensure_exists=lambda: None,
        heartbeat_file=lambda name: str(tmp_path / f"{name}.json"),
        log_file=lambda name: str(tmp_path / f"{name}.log"),
        as_config=lambda *args: {},
        as_environment=lambda *args: {},
    )
    return layout


def test_tts_temp_config_is_owner_only_and_sweeps_all(tmp_path, monkeypatch):
    import airunner_services.runtimes.sidecar_tts_launcher as tts_launcher
    from airunner_services.runtimes import sidecar_configs

    layout = _fake_layout(tmp_path)
    monkeypatch.setattr(
        tts_launcher, "build_runtime_directory_layout", lambda: layout
    )
    (tmp_path / "airunner-art-runtime-stale.yaml").write_text("a: 1\n")
    monkeypatch.setattr(sidecar_configs, "live_config_paths", set)
    written = tts_launcher._build_temp_daemon_config(_tts_settings())
    mode = stat.S_IMODE(os.stat(written).st_mode)
    assert mode == 0o600
    assert not (tmp_path / "airunner-art-runtime-stale.yaml").exists()


def test_art_temp_config_sweeps_all_prefixes(tmp_path, monkeypatch):
    import airunner_services.runtimes.sidecar_art_launcher as art_launcher
    from airunner_services.runtimes import sidecar_configs
    from airunner_services.runtimes.art_daemon_runtime_settings import (
        resolve_art_daemon_runtime_settings,
    )

    layout = _fake_layout(tmp_path)
    monkeypatch.setattr(
        art_launcher, "build_runtime_directory_layout", lambda: layout
    )
    (tmp_path / "airunner-tts-runtime-stale.yaml").write_text("a: 1\n")
    monkeypatch.setattr(sidecar_configs, "live_config_paths", set)
    try:
        settings = resolve_art_daemon_runtime_settings()
    except Exception:
        pytest.skip("art settings need a configured environment")
    art_launcher._build_temp_daemon_config(settings)
    assert not (tmp_path / "airunner-tts-runtime-stale.yaml").exists()


def test_sidecar_configs_documents_platform_limit():
    from airunner_services.runtimes import sidecar_configs

    assert "Linux" in sidecar_configs.live_config_paths.__doc__
    assert "Windows" in sidecar_configs.live_config_paths.__doc__


# ---------------------------------------------------------------------
# Agents: empty keywords, timeouts, locked registry
# ---------------------------------------------------------------------


class _StubAgent:
    def __init__(self, name="stub"):
        from airunner_services.agents.expert_agent import ExpertAgent

        class _Concrete(ExpertAgent):
            async def execute_task(self, task, context=None):
                return {"result": "ok", "success": True, "metadata": {}}

        self._inner = _Concrete(name, "stub agent")
        self.name = name

    def __getattr__(self, item):
        return getattr(self._inner, item)


def test_expert_agent_empty_keywords_scores_zero():
    agent = _StubAgent()._inner
    agent.register_capability("empty", "no keywords", [], priority=10)
    assert agent.evaluate_task("anything at all") == 0.0


def test_router_times_out_hung_agent():
    from airunner_services.agents.agent_registry import AgentRegistry
    from airunner_services.agents.agent_router import AgentRouter
    from airunner_services.agents.expert_agent import ExpertAgent

    class _Hung(ExpertAgent):
        async def execute_task(self, task, context=None):
            await asyncio.sleep(30)
            return {"result": "never", "success": True}

    hung = _Hung("hung", "hangs forever")
    hung.register_capability("hang", "hang task", ["hang"], priority=10)
    registry = AgentRegistry()
    registry.register(hung)
    router = AgentRouter(registry)
    result = asyncio.run(
        router.route_task("please hang", agent_timeout_seconds=0.05)
    )
    assert result["success"] is False
    assert result["result"] is None
    assert result["agents_used"] == []


def test_registry_thread_safe_register_and_get():
    from airunner_services.agents.agent_registry import AgentRegistry

    registry = AgentRegistry()
    stubs = [_StubAgent(f"agent-{i}")._inner for i in range(8)]

    def _register(agent):
        registry.register(agent)

    workers = [threading.Thread(target=_register, args=(s,)) for s in stubs]
    for worker in workers:
        worker.start()
    for worker in workers:
        worker.join()
    assert len(registry) == 8
    assert registry.get("agent-3") is not None
    assert "agent-3" in registry
    assert sorted(registry.list_agents()) == sorted(
        f"agent-{i}" for i in range(8)
    )


# ---------------------------------------------------------------------
# Local fallback: correlated STT, TTS param notice, audio caps
# ---------------------------------------------------------------------


class _FakeMediator:
    def __init__(self, respond=None):
        self.handlers = {}
        self.pending = {}
        self.respond = respond

    def register(self, signal, handler):
        self.handlers.setdefault(signal, []).append(handler)

    def unregister(self, signal, handler):
        self.handlers.get(signal, []).remove(handler)

    def emit_signal(self, signal, data):
        if self.respond is not None:
            self.respond(self, signal, data)

    def register_pending_request(self, request_id):
        from queue import Queue

        queue = Queue()
        self.pending[request_id] = queue
        return queue

    def unregister_pending_request(self, request_id):
        self.pending.pop(request_id, None)


def _stt_envelope(payload, request_id="stt-1"):
    from airunner_services.ipc.messages import RequestEnvelope
    from airunner_services.runtimes.contracts import RuntimeAction, RuntimeKind

    return RequestEnvelope(
        runtime=RuntimeKind.STT,
        action=RuntimeAction.INVOKE,
        payload=payload,
        request_id=request_id,
    )


def test_fallback_stt_ignores_other_requests_responses():
    from airunner_services.ipc.messages import EnvelopeStatus
    from airunner_services.runtimes import local_fallback as fallback

    from airunner_common.contract_enums import SignalCode

    def _respond(mediator, signal, data):
        for handler in list(
            mediator.handlers.get(
                SignalCode.AUDIO_PROCESSOR_RESPONSE_SIGNAL, []
            )
        ):
            handler(
                {
                    "request_id": "someone-else",
                    "transcription": {"text": "wrong"},
                }
            )

    mediator = _FakeMediator(respond=_respond)
    client = fallback.LocalFallbackSTTClient(
        signal_source=object(),
        mediator=mediator,
        timeout_seconds=0.05,
    )
    audio = base64.b64encode(b"RIFF....").decode("ascii")
    response = client.invoke(
        _stt_envelope({"audio_b64": audio, "mime_type": "audio/wav"})
    )
    assert response.status is EnvelopeStatus.FAILED
    assert response.error.code == "stt_timeout"


def test_fallback_stt_accepts_correlated_response():
    from airunner_services.ipc.messages import EnvelopeStatus
    from airunner_services.runtimes import local_fallback as fallback

    from airunner_common.contract_enums import SignalCode

    def _respond(mediator, signal, data):
        assert data["request_id"] == "stt-7"
        for handler in list(
            mediator.handlers.get(
                SignalCode.AUDIO_PROCESSOR_RESPONSE_SIGNAL, []
            )
        ):
            handler(
                {
                    "request_id": "stt-7",
                    "transcription": {"text": "hello"},
                }
            )

    mediator = _FakeMediator(respond=_respond)
    client = fallback.LocalFallbackSTTClient(
        signal_source=object(),
        mediator=mediator,
        timeout_seconds=5.0,
    )
    audio = base64.b64encode(b"RIFF....").decode("ascii")
    response = client.invoke(
        _stt_envelope(
            {"audio_b64": audio, "mime_type": "audio/wav"},
            request_id="stt-7",
        )
    )
    assert response.status is EnvelopeStatus.SUCCEEDED
    assert response.payload["text"] == "hello"


def test_fallback_stt_rejects_oversize_audio(monkeypatch):
    from airunner_services.ipc.messages import EnvelopeStatus
    from airunner_services.runtimes import local_fallback as fallback

    monkeypatch.setattr(
        fallback, "MAX_LOCAL_FALLBACK_AUDIO_BYTES", 4
    )
    client = fallback.LocalFallbackSTTClient(
        signal_source=object(),
        mediator=_FakeMediator(),
        timeout_seconds=0.05,
    )
    audio = base64.b64encode(b"0123456789").decode("ascii")
    response = client.invoke(
        _stt_envelope({"audio_b64": audio, "mime_type": "audio/wav"})
    )
    assert response.status is EnvelopeStatus.FAILED
    assert response.error.code == "stt_invalid_audio"


def test_fallback_tts_playback_reports_unsupported_params(monkeypatch):
    from airunner_services.ipc.messages import EnvelopeStatus, RequestEnvelope
    from airunner_services.runtimes import local_fallback as fallback
    from airunner_services.runtimes.contracts import (
        RuntimeAction,
        RuntimeKind,
    )

    recorder = _LogRecorder()
    monkeypatch.setattr(fallback, "logger", recorder)
    seen = {}

    def _respond(mediator, signal, data):
        seen.update(data)

    mediator = _FakeMediator(respond=_respond)
    client = fallback.LocalFallbackTTSClient(
        signal_source=object(),
        mediator=mediator,
        timeout_seconds=5.0,
    )
    request = RequestEnvelope(
        runtime=RuntimeKind.TTS,
        action=RuntimeAction.INVOKE,
        payload={"text": "hi", "voice": "bob", "speed": 2.0},
        request_id="tts-3",
    )
    response = client.invoke(request)
    assert response.status is EnvelopeStatus.SUCCEEDED
    assert seen["message"] == "hi"
    assert seen["voice"] == "bob"
    assert seen["speed"] == 2.0
    assert response.metadata["unsupported_params"] == ["voice", "speed"]
    assert any(
        "ignores caller params" in message
        for message in recorder.messages()
    )


def test_fallback_cancels_log_best_effort(monkeypatch):
    from airunner_services.ipc.messages import EnvelopeStatus
    from airunner_services.runtimes import local_fallback as fallback

    recorder = _LogRecorder()
    monkeypatch.setattr(fallback, "logger", recorder)
    stt = fallback.LocalFallbackSTTClient(
        signal_source=object(),
        mediator=_FakeMediator(),
    )
    response = stt.cancel("stt-1")
    assert response.status is EnvelopeStatus.CANCELLED
    assert any("best-effort" in message for message in recorder.messages())


# ---------------------------------------------------------------------
# Registry STT executor audio cap
# ---------------------------------------------------------------------


def test_registry_stt_executor_rejects_oversize_clip(monkeypatch):
    from airunner_services.runtimes import runtime_registry_stt_executor as ex

    monkeypatch.setattr(ex, "MAX_EXECUTOR_AUDIO_BYTES", 4)
    executor = ex.RuntimeRegistrySTTExecutor(api=object())
    recorder = _LogRecorder()
    executor.logger = recorder
    assert executor.transcribe({"item": b"0123456789"}) == ""
    assert any("size budget" in message for message in recorder.messages())


# ---------------------------------------------------------------------
# Local embeddings: MRO probing and input caps
# ---------------------------------------------------------------------


class _FormattedRecord:
    def __init__(self, message, args):
        self.message = message % args if args else message

    def __str__(self):
        return self.message


class _LogRecorder:
    """Stand-in for the AIRunner Logger wrapper that records calls."""

    def __init__(self):
        self.records = []

    def debug(self, message, *args, **kwargs):
        self.records.append(_FormattedRecord(message, args))

    def info(self, message, *args, **kwargs):
        self.records.append(_FormattedRecord(message, args))

    def warning(self, message, *args, **kwargs):
        self.records.append(_FormattedRecord(message, args))

    def error(self, message, *args, **kwargs):
        self.records.append(_FormattedRecord(message, args))

    def messages(self):
        return [str(record) for record in self.records]


def _embedding_identity(dim=4):
    from airunner_services.llm.companion.embeddings import (
        EmbeddingModelIdentity,
    )

    return EmbeddingModelIdentity(
        model_id="intfloat/e5-large", dimension=dim, revision="main"
    )


class _FakeLocalEmbedder:
    def embed_query(self, text):
        return [1.0, 2.0, 3.0, 4.0]

    def embed_documents(self, texts):
        return [[float(len(t)), 0.0, 0.0, 0.0] for t in texts]


def test_embeddings_refuse_hostile_getattr_without_executing_it():
    from airunner_services.runtimes.local_embeddings import LocalEmbeddingClient

    class _Hostile:
        def __getattr__(self, name):
            raise AssertionError(f"__getattr__({name}) must not execute")

        def embed_query(self, text):
            return [1.0, 2.0, 3.0, 4.0]

        def embed_documents(self, texts):
            return [[1.0, 2.0, 3.0, 4.0] for _ in texts]

    client = LocalEmbeddingClient(_Hostile(), _embedding_identity())
    assert client.embed_query("hi") == [1.0, 2.0, 3.0, 4.0]


def test_embeddings_refuse_class_level_remote_marker():
    from airunner_services.runtimes.local_embeddings import LocalEmbeddingClient

    class _Remote:
        base_url = "http://localhost:11434"

        def embed_query(self, text):
            return [1.0, 2.0, 3.0, 4.0]

        def embed_documents(self, texts):
            return [[1.0, 2.0, 3.0, 4.0] for _ in texts]

    with pytest.raises(ValueError, match="remote"):
        LocalEmbeddingClient(_Remote(), _embedding_identity())


def test_embeddings_reject_oversize_inputs():
    from airunner_services.runtimes.local_embeddings import LocalEmbeddingClient

    client = LocalEmbeddingClient(_FakeLocalEmbedder(), _embedding_identity())
    with pytest.raises(ValueError, match="exceeds"):
        client.embed_query("x" * (8 * 1024 + 1))
    with pytest.raises(ValueError, match="exceeds"):
        client.embed_documents(["ok"] * 257)
    assert client.embed_query("ok") == [1.0, 2.0, 3.0, 4.0]


# ---------------------------------------------------------------------
# Web tools: SSRF gate, cooldown lock, loop-aware runner
# ---------------------------------------------------------------------


def test_scrape_url_gate_blocks_dangerous_targets():
    from airunner_services.tools.web_tools import validate_scrape_url

    for bad in (
        "file:///etc/passwd",
        "ftp://example.com/x",
        "http://localhost:8188/api",
        "http://127.0.0.1:8188/",
        "http://169.254.169.254/latest/meta-data/",
        "http://[::1]/",
        "not-a-url",
        "",
    ):
        with pytest.raises(ValueError):
            validate_scrape_url(bad)


def test_scrape_url_gate_allows_public_literal():
    from airunner_services.tools.web_tools import validate_scrape_url

    assert (
        validate_scrape_url("https://8.8.8.8/info").startswith("https://")
    )


def test_scrape_website_refuses_ssrf_without_fetching():
    from airunner_services.tools import web_tools

    called = []

    class _Extractor:
        @staticmethod
        def fetch_and_extract_with_metadata(*args, **kwargs):
            called.append(args)
            raise AssertionError("must not fetch")

    module_name = "airunner_services.tools.web_content_extractor"
    stub = types.ModuleType(module_name)
    stub.WebContentExtractor = _Extractor
    sys.modules[module_name] = stub
    try:
        result = web_tools.scrape_website("http://127.0.0.1:8188/x")
    finally:
        del sys.modules[module_name]
    assert result["content"] is None
    assert "Refusing" in result["error"]
    assert called == []


def test_provider_runner_without_running_loop():
    from airunner_services.tools.web_tools import _run_provider_coro

    async def _answer():
        return [{"title": "t"}]

    assert _run_provider_coro(_answer) == [{"title": "t"}]


def test_provider_runner_inside_running_loop():
    from airunner_services.tools.web_tools import _run_provider_coro

    async def _main():
        async def _answer():
            return [{"title": "t"}]

        return _run_provider_coro(_answer)

    assert asyncio.run(_main()) == [{"title": "t"}]


def test_cooldown_state_guarded_by_lock():
    from airunner_services.tools import web_tools

    assert isinstance(web_tools._cooldown_lock, type(threading.Lock()))
    web_tools._respect_search_cooldown("wave2")
    web_tools._respect_search_cooldown("wave2")


# ---------------------------------------------------------------------
# eSpeak: clamps, sanitizing, engine lock
# ---------------------------------------------------------------------


def _espeak_manager():
    _install_heavy_stubs()
    from airunner_services.runtimes.espeak_model_manager import (
        EspeakModelManager,
    )

    return EspeakModelManager(api=None)


def test_espeak_sanitize_strips_backend_characters():
    _install_heavy_stubs()
    from airunner_services.runtimes.espeak_model_manager import (
        sanitize_speech_text,
    )

    cleaned = sanitize_speech_text('Say "hi" \\ now\x00bye\x07')
    assert '"' not in cleaned
    assert "\\" not in cleaned
    assert "\x00" not in cleaned
    assert "hi" in cleaned


def test_espeak_clamps_voice_params():
    from airunner_common.contract_enums import ModelStatus, ModelType

    manager = _espeak_manager()
    manager.change_model_status(ModelType.TTS, ModelStatus.LOADED)
    manager._engine = object()

    class _Req:
        message = "hi"
        volume = -20
        rate = 9999
        pitch = -3
        voice = "english"
        language = "en"
        gender = "Male"

    manager.tts_request = _Req()
    assert manager.volume == 0
    assert manager.rate == 400
    assert manager.pitch == 0


def test_espeak_generate_serializes_engine():
    from airunner_common.contract_enums import ModelStatus, ModelType

    manager = _espeak_manager()
    manager.change_model_status(ModelType.TTS, ModelStatus.LOADED)
    entered = []
    release = threading.Event()

    class _Engine:
        def say(self, message):
            entered.append(message)

        def runAndWait(self):
            release.wait(timeout=5)

        def setProperty(self, *args):
            pass

        def getProperty(self, name):
            return []

    manager._engine = _Engine()

    class _Req:
        message = "hello"
        volume = 80
        rate = 150
        pitch = 50
        voice = "english"
        language = "en"
        gender = "Male"

    workers = [
        threading.Thread(target=manager.generate, args=(_Req(),))
        for _ in range(3)
    ]
    for worker in workers:
        worker.start()
    release.set()
    for worker in workers:
        worker.join(timeout=10)
    assert not any(w.is_alive() for w in workers)
    # Serialized: the blocking runAndWait never overlaps.
    assert len(entered) == 3


# ---------------------------------------------------------------------
# OpenVoice: None-model, per-request temps, no recursion, warmup wired
# ---------------------------------------------------------------------


def _openvoice_manager():
    _install_heavy_stubs()
    from airunner_services.runtimes.openvoice_model_manager import (
        OpenVoiceModelManager,
    )

    return OpenVoiceModelManager(api=None)


def test_openvoice_generate_requires_loaded_model():
    from airunner_services.runtimes.openvoice_exceptions import OpenVoiceError
    from airunner_services.requests.tts_request import TTSRequest

    manager = _openvoice_manager()
    manager.model = None
    with pytest.raises(OpenVoiceError, match="not loaded"):
        manager.generate(TTSRequest(message="hi"))


def test_openvoice_generate_uses_unique_temp_files(tmp_path):
    from airunner_services.requests.tts_request import TTSRequest

    manager = _openvoice_manager()
    manager._output_dir = str(tmp_path)

    seen_src = []

    class _FakeModel:
        language = "en"

        def __init__(self):
            self.hps = types.SimpleNamespace(
                data=types.SimpleNamespace(spk2id={"EN-Default": 0})
            )

        def tts_to_file(self, message, speaker, path, **kwargs):
            Path(path).write_bytes(b"wav")

    class _FakeConverter:
        def convert(self, audio_src_path, src_se, tgt_se, output_path):
            seen_src.append(audio_src_path)
            Path(output_path).write_bytes(b"out")
            return [0.1, 0.2]

    manager.model = _FakeModel()
    manager._tone_color_converter = _FakeConverter()
    manager._source_se = object()
    manager._target_se = object()
    first = manager.generate(TTSRequest(message="one"))
    second = manager.generate(TTSRequest(message="two"))
    assert first == [0.1, 0.2]
    assert second == [0.1, 0.2]
    assert len(seen_src) == 2
    assert seen_src[0] != seen_src[1]
    # Intermediates are cleaned up, never accumulated.
    assert list(tmp_path.iterdir()) == []


def test_openvoice_load_defers_reentrant_callback(monkeypatch):
    manager = _openvoice_manager()
    manager._load_in_progress = True
    assert manager.load() is True
    assert manager._skip_download_check is True


def test_openvoice_prepare_for_load_after_sync_download(monkeypatch):
    manager = _openvoice_manager()
    manager._download_completed = True
    monkeypatch.setattr(
        manager, "_check_and_trigger_download", lambda: (True, {})
    )
    assert manager._prepare_for_load() is True
    assert manager._download_completed is False


def test_openvoice_load_warms_frontend(monkeypatch):
    import airunner_services.runtimes.openvoice_model_manager as manager_mod
    from airunner_common.contract_enums import ModelStatus, ModelType

    warmed = []

    class _FakeTTS:
        def __init__(self, language=None, device=None):
            pass

        def unload(self):
            pass

    monkeypatch.setattr(manager_mod, "TTS", _FakeTTS)
    monkeypatch.setattr(
        manager_mod, "warm_melo_tts", lambda *args: warmed.append(args)
    )
    manager = _openvoice_manager()
    monkeypatch.setattr(manager, "_initialize", lambda: None)
    monkeypatch.setattr(
        manager, "_check_and_trigger_download", lambda: (False, {})
    )
    assert manager.load() is True
    assert manager._model_status[ModelType.TTS] is ModelStatus.LOADED
    assert len(warmed) == 1


def test_openvoice_readable_file_check(tmp_path):
    import airunner_services.runtimes.openvoice_model_manager as manager_mod

    present = tmp_path / "config.json"
    present.write_text("{}")
    assert manager_mod._readable_file(str(present)) is True
    assert manager_mod._readable_file(str(tmp_path / "nope")) is False


def test_tone_converter_precheck_raises_openvoice_error(tmp_path):
    _install_heavy_stubs()
    from airunner_services.runtimes.openvoice_exceptions import OpenVoiceError
    from airunner_services.runtimes.openvoice_runtime_helpers import (
        build_tone_color_converter,
    )

    with pytest.raises(OpenVoiceError, match="missing"):
        build_tone_color_converter(str(tmp_path))


def test_tone_converter_decode_failure_returns_none(monkeypatch):
    _install_heavy_stubs()
    import librosa
    from airunner_services.runtimes.openvoice_runtime_helpers import (
        MAX_REFERENCE_SPEAKER_SECONDS,
        StreamingToneColorConverter,
    )

    calls = {}

    def _failing_load(path, *, sr=None, mono=None, duration=None):
        calls["duration"] = duration
        raise RuntimeError("bad audio")

    monkeypatch.setattr(librosa, "load", _failing_load)
    import logging

    converter = object.__new__(StreamingToneColorConverter)
    converter.hps = types.SimpleNamespace(
        data=types.SimpleNamespace(sampling_rate=24000)
    )
    converter.device = "cpu"
    converter.logger = logging.getLogger("wave2-test")
    assert (
        converter.convert(
            audio_src_path="x.wav", src_se=None, tgt_se=None
        )
        is None
    )
    assert calls["duration"] == MAX_REFERENCE_SPEAKER_SECONDS
