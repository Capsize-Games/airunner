"""Functional end-to-end TTS test using the real headless daemon."""

from __future__ import annotations

import io
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
import wave
from pathlib import Path

import pytest
import yaml


_API_ROOT = Path(__file__).resolve().parents[1]
_PROJECT_ROOT = _API_ROOT.parent

for _path in (
    _API_ROOT / "src",
    _PROJECT_ROOT / "services" / "src",
    _PROJECT_ROOT / "model" / "src",
    _PROJECT_ROOT / "native" / "src",
):
    _path_str = str(_path)
    if _path_str not in sys.path:
        sys.path.append(_path_str)


_BUNDLED_REFERENCE_SPEAKER = (
    _PROJECT_ROOT
    / "services"
    / "src"
    / "airunner_services"
    / "assets"
    / "reference_speakers"
    / "bobross.wav"
)

_DEFAULT_TTS_MODEL_PATH = (
    Path.home()
    / ".local"
    / "share"
    / "airunner"
    / "text"
    / "models"
    / "tts"
    / "openvoice"
)


def _free_tcp_port() -> int:
    """Return one free local TCP port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _tts_model_path() -> Path:
    """Return the local OpenVoice model path used for the test."""
    configured = os.environ.get("AIRUNNER_REAL_TTS_MODEL_PATH", "")
    if configured.strip():
        return Path(configured).expanduser().resolve()
    return _DEFAULT_TTS_MODEL_PATH


def _daemon_env(model_path: Path) -> dict[str, str]:
    """Return one environment for the real headless daemon."""
    pythonpath_entries = [
        str(_API_ROOT / "src"),
        str(_PROJECT_ROOT / "services" / "src"),
        str(_PROJECT_ROOT / "model" / "src"),
        str(_PROJECT_ROOT / "native" / "src"),
        str(_PROJECT_ROOT / "src"),
    ]
    existing = os.environ.get("PYTHONPATH", "").strip()
    if existing:
        pythonpath_entries.append(existing)

    env = os.environ.copy()
    env.update(
        {
            "PYTHONPATH": os.pathsep.join(pythonpath_entries),
            "AIRUNNER_DISABLE_STALE_DAEMON_CHECK": "1",
            "AIRUNNER_INSECURE_NO_AUTH": "1",
            "AIRUNNER_LLM_ON": "0",
            "AIRUNNER_SD_ON": "0",
            "AIRUNNER_STT_ON": "0",
            "AIRUNNER_CN_ON": "0",
            "AIRUNNER_KNOWLEDGE_ON": "0",
            "AIRUNNER_TTS_ON": "1",
            "AIRUNNER_TTS_MODEL_TYPE": "OpenVoice",
            "AIRUNNER_TTS_MODEL_PATH": str(model_path),
            "AIRUNNER_NO_PRELOAD": "1",
            "AIRUNNER_API_ACCESS_LOG": "1",
            "AIRUNNER_LOG_LEVEL": "INFO",
        }
    )
    return env


def _daemon_config(port: int, heartbeat_file: Path) -> dict[str, object]:
    """Return one minimal daemon configuration for the test."""
    return {
        "server": {
            "host": "127.0.0.1",
            "port": port,
            "enable_cors": True,
            "allowed_origins": [
                "http://localhost:*",
                "http://127.0.0.1:*",
            ],
        },
        "health": {
            "heartbeat_interval": 5,
            "heartbeat_file": str(heartbeat_file),
        },
    }


def _daemon_output(log_path: Path) -> str:
    """Return the tail of the daemon log for assertion failures."""
    if not log_path.exists():
        return "<daemon log unavailable>"
    lines = log_path.read_text(
        encoding="utf-8",
        errors="replace",
    ).splitlines()
    return "\n".join(lines[-120:])


def _wait_for_health(port: int, process: subprocess.Popen, log_path: Path) -> None:
    """Wait until the daemon health endpoint answers successfully."""
    deadline = time.time() + 45
    url = f"http://127.0.0.1:{port}/health"
    while time.time() < deadline:
        if process.poll() is not None:
            pytest.fail(
                "Daemon exited before startup completed.\n"
                f"{_daemon_output(log_path)}"
            )
        try:
            with urllib.request.urlopen(url, timeout=1) as response:
                if response.status == 200:
                    return
        except OSError:
            time.sleep(0.25)
            continue
        time.sleep(0.25)

    pytest.fail(
        "Timed out waiting for daemon health.\n"
        f"{_daemon_output(log_path)}"
    )


def _post_json(url: str, payload: dict[str, object]) -> tuple[int, bytes, str]:
    """POST one JSON payload and return status, body, and content type."""
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return (
                int(response.status),
                response.read(),
                response.headers.get_content_type(),
            )
    except urllib.error.HTTPError as error:
        return (
            int(error.code),
            error.read(),
            error.headers.get_content_type(),
        )


def _get_json(url: str) -> tuple[int, dict[str, object]]:
    """Return the decoded JSON payload for one GET request."""
    with urllib.request.urlopen(url, timeout=30) as response:
        return int(response.status), json.loads(response.read().decode("utf-8"))


def _stop_process(process: subprocess.Popen) -> None:
    """Stop one daemon process started by the test."""
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=10)


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.timeout(120)
def test_openvoice_synthesize_end_to_end_without_gui_or_llm() -> None:
    """Load OpenVoice and synthesize real WAV audio through the API."""
    if not _BUNDLED_REFERENCE_SPEAKER.is_file():
        pytest.fail(
            "Bundled Bob Ross reference speaker is missing: "
            f"{_BUNDLED_REFERENCE_SPEAKER}"
        )

    model_path = _tts_model_path()
    if not model_path.is_dir():
        pytest.skip(
            "Real OpenVoice assets are required at "
            f"{model_path}"
        )

    port = _free_tcp_port()
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        config_path = temp_path / "daemon.yaml"
        log_path = temp_path / "daemon.log"
        config_path.write_text(
            yaml.safe_dump(
                _daemon_config(
                    port,
                    temp_path / "daemon.heartbeat",
                )
            ),
            encoding="utf-8",
        )

        with open(log_path, "w", encoding="utf-8") as log_handle:
            process = subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "airunner_services.daemon",
                    "--config",
                    str(config_path),
                ],
                cwd=str(_PROJECT_ROOT),
                env=_daemon_env(model_path),
                stdout=log_handle,
                stderr=subprocess.STDOUT,
            )

        try:
            _wait_for_health(port, process, log_path)

            load_status, load_body, _load_type = _post_json(
                f"http://127.0.0.1:{port}/api/v1/daemon/runtimes/tts/load",
                {
                    "provider": "local",
                    "deployment_mode": "local_fallback",
                    "request_id": "functional-tts-load",
                    "metadata": {"model_type": "OpenVoice"},
                },
            )

            assert load_status == 200, _daemon_output(log_path)
            load_payload = json.loads(load_body.decode("utf-8"))
            assert load_payload["status"] == "succeeded"
            assert load_payload["payload"]["model_status"] == "Loaded"

            synth_status, audio_bytes, content_type = _post_json(
                f"http://127.0.0.1:{port}/api/v1/tts/synthesize",
                {
                    "text": "This is a real OpenVoice synthesis test.",
                    "model_type": "OpenVoice",
                    "request_id": "functional-tts-synth",
                },
            )

            assert synth_status == 200, _daemon_output(log_path)
            assert content_type == "audio/wav"
            assert audio_bytes[:4] == b"RIFF"
            assert audio_bytes[8:12] == b"WAVE"

            with wave.open(io.BytesIO(audio_bytes), "rb") as wav_file:
                assert wav_file.getnchannels() >= 1
                assert wav_file.getframerate() > 0
                assert wav_file.getnframes() > 0

            runtime_status, runtime_payload = _get_json(
                "http://127.0.0.1:"
                f"{port}/api/v1/daemon/runtimes/tts"
                "?provider=local&deployment_mode=local_fallback"
            )

            assert runtime_status == 200
            assert runtime_payload["status"] == "ready"
            assert runtime_payload["loaded"] is True
            assert runtime_payload["metadata"]["model_status"] == "Loaded"

            unload_status, unload_body, _unload_type = _post_json(
                f"http://127.0.0.1:{port}/api/v1/daemon/runtimes/tts/unload",
                {
                    "provider": "local",
                    "deployment_mode": "local_fallback",
                    "request_id": "functional-tts-unload",
                    "metadata": {"model_type": "OpenVoice"},
                },
            )

            assert unload_status == 200, _daemon_output(log_path)
            unload_payload = json.loads(unload_body.decode("utf-8"))
            assert unload_payload["status"] == "succeeded"
            assert unload_payload["payload"]["model_status"] == "Unloaded"
        finally:
            _stop_process(process)