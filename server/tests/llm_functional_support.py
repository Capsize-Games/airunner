"""Shared helpers for real daemon-backed LLM functional tests."""

from __future__ import annotations

import json
import os
import re
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

import pytest
import yaml


_SERVICES_ROOT = Path(__file__).resolve().parents[1]
_PROJECT_ROOT = _SERVICES_ROOT.parent

for _path in (
    _PROJECT_ROOT / "services" / "src",
):
    _path_str = str(_path)
    if _path_str not in sys.path:
        sys.path.append(_path_str)

from airunner_services.llm.provider_config import LLMProviderConfig
from airunner_services.settings import AIRUNNER_BASE_PATH


BUNDLED_REFERENCE_SPEAKER = (
    _PROJECT_ROOT
    / "services"
    / "src"
    / "airunner_services"
    / "assets"
    / "reference_speakers"
    / "bobross.wav"
)

DEFAULT_TTS_MODEL_PATH = (
    Path.home()
    / ".local"
    / "share"
    / "airunner"
    / "text"
    / "models"
    / "tts"
)
FUNCTIONAL_TEST_LOG_ROOT = _PROJECT_ROOT / "logs" / "functional-tests"


@dataclass(frozen=True)
class DaemonHandle:
    """Represent one running daemon process for a functional test."""

    port: int
    log_path: Path
    process: subprocess.Popen

    @property
    def base_url(self) -> str:
        """Return the local HTTP base URL for the daemon."""
        return f"http://127.0.0.1:{self.port}"


def llm_artifact_path(model_id: str) -> Path:
    """Return the expected local artifact path for one model id."""
    artifact_path = LLMProviderConfig.get_expected_local_artifact_path(
        AIRUNNER_BASE_PATH,
        "local",
        model_id=model_id,
    )
    return Path(artifact_path).expanduser().resolve()


def tts_model_path() -> Path:
    """Return the local TTS asset root used for functional tests."""
    configured = os.environ.get("AIRUNNER_REAL_TTS_MODEL_PATH", "")
    if configured.strip():
        path = Path(configured).expanduser().resolve()
    else:
        path = DEFAULT_TTS_MODEL_PATH
    if path.name == "openvoice" and (path / "checkpoints_v2").is_dir():
        return path.parent
    return path


def daemon_env(
    *,
    llm_on: bool = True,
    tts_on: bool = False,
    openvoice_model_path: Path | None = None,
    extra_env: dict[str, str] | None = None,
) -> dict[str, str]:
    """Return one environment for the real daemon."""
    pythonpath_entries = [
        str(_PROJECT_ROOT / "services" / "src"),
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
            "AIRUNNER_LLM_ON": "1" if llm_on else "0",
            "AIRUNNER_SD_ON": "0",
            "AIRUNNER_STT_ON": "0",
            "AIRUNNER_CN_ON": "0",
            "AIRUNNER_KNOWLEDGE_ON": "0",
            "AIRUNNER_TTS_ON": "1" if tts_on else "0",
            "AIRUNNER_NO_PRELOAD": "1",
            "AIRUNNER_API_ACCESS_LOG": "1",
            "AIRUNNER_LOG_LEVEL": "INFO",
        }
    )
    if tts_on:
        resolved_path = openvoice_model_path or tts_model_path()
        env.update(
            {
                "AIRUNNER_TTS_MODEL_TYPE": "OpenVoice",
                "AIRUNNER_TTS_MODEL_PATH": str(resolved_path),
            }
        )
    if extra_env:
        env.update(extra_env)
    return env


def daemon_output(log_path: Path) -> str:
    """Return the tail of one daemon log for assertion failures."""
    if not log_path.exists():
        return "<daemon log unavailable>"
    lines = log_path.read_text(
        encoding="utf-8",
        errors="replace",
    ).splitlines()
    return "\n".join(lines[-120:])


def wait_for_log_text(
    log_path: Path,
    needle: str,
    *,
    timeout_seconds: float = 30.0,
) -> None:
    """Wait until one daemon log file contains one expected string."""
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        if log_path.exists():
            contents = log_path.read_text(
                encoding="utf-8",
                errors="replace",
            )
            if needle in contents:
                return
        time.sleep(0.25)

    pytest.fail(
        f"Timed out waiting for daemon log text: {needle}\n"
        f"{daemon_output(log_path)}"
    )


def post_json(
    url: str,
    payload: dict[str, object],
    *,
    timeout_seconds: float = 300.0,
) -> tuple[int, bytes, str]:
    """POST one JSON payload and return status, body, and content type."""
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
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


def stop_process(process: subprocess.Popen) -> None:
    """Stop one daemon process started by a functional test."""
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=10)


def _functional_test_run_dir() -> Path:
    """Return one repo-local directory for daemon test artifacts."""
    FUNCTIONAL_TEST_LOG_ROOT.mkdir(parents=True, exist_ok=True)
    return Path(
        tempfile.mkdtemp(
            prefix="daemon-",
            dir=str(FUNCTIONAL_TEST_LOG_ROOT),
        )
    )


@contextmanager
def started_daemon(env: dict[str, str]) -> Iterator[DaemonHandle]:
    """Start one real daemon subprocess and yield its connection details."""
    port = _free_tcp_port()
    temp_path = _functional_test_run_dir()
    config_path = temp_path / "daemon.yaml"
    log_path = temp_path / "daemon.log"
    config_path.write_text(
        yaml.safe_dump(_daemon_config(port, temp_path / "daemon.heartbeat")),
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
            env=env,
            stdout=log_handle,
            stderr=subprocess.STDOUT,
        )

    try:
        _wait_for_health(port, process, log_path)
        yield DaemonHandle(port=port, log_path=log_path, process=process)
    finally:
        stop_process(process)


def visible_llm_message(message: str) -> str:
    """Return one assistant-visible reply without status or thinking text."""
    without_thinking = re.sub(
        r"<think>.*?</think>",
        "",
        message,
        flags=re.DOTALL | re.IGNORECASE,
    )
    lines = []
    for raw_line in without_thinking.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("🔧") or line.startswith("✅"):
            continue
        lines.append(line)
    return " ".join(lines).strip()


def visible_digits(message: str) -> str:
    """Return only the visible numeric portion of one LLM response."""
    return re.sub(r"[^0-9]", "", visible_llm_message(message))


def visible_last_number(message: str) -> str:
    """Return the last visible number-like token from one LLM response."""
    matches = re.findall(r"\d(?:[\s.,_-]*\d)*", visible_llm_message(message))
    if not matches:
        return ""
    return re.sub(r"[^0-9]", "", matches[-1])


def llm_request_payload(
    model_id: str,
    *,
    do_tts_reply: bool,
) -> dict[str, object]:
    """Return one stable legacy LLM request payload for functional tests."""
    prompt = "Reply with exactly the single digit 7."
    if model_id.startswith("qwen3"):
        prompt = f"/no_think\n{prompt}"

    return {
        "model": model_id,
        "prompt": prompt,
        "action": "CHAT",
        "stream": False,
        "do_tts_reply": do_tts_reply,
        "system_prompt": "Reply with one character only.",
        "enable_thinking": False,
        "do_sample": False,
        "temperature": 0.1,
        "top_p": 0.1,
        "max_new_tokens": 16,
        "ephemeral": True,
        "use_memory": False,
    }


def combined_llama_env_overrides(model_id: str) -> dict[str, str]:
    """Return stable combined-mode llama.cpp overrides for one model."""
    overrides = {
        "qwen3.5-9b": {
            "AIRUNNER_GGUF_N_CTX": "4096",
            "AIRUNNER_GGUF_N_GPU_LAYERS": "10",
        },
        "gpt-oss-20b": {
            "AIRUNNER_GGUF_N_CTX": "4096",
            "AIRUNNER_GGUF_N_GPU_LAYERS": "0",
        },
    }
    return dict(overrides.get(model_id, {}))


def _free_tcp_port() -> int:
    """Return one free local TCP port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _daemon_config(port: int, heartbeat_file: Path) -> dict[str, object]:
    """Return one minimal daemon configuration for a functional test."""
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


def _wait_for_health(port: int, process: subprocess.Popen, log_path: Path) -> None:
    """Wait until the daemon health endpoint answers successfully."""
    deadline = time.time() + 45
    url = f"http://127.0.0.1:{port}/health"
    while time.time() < deadline:
        if process.poll() is not None:
            pytest.fail(
                "Daemon exited before startup completed.\n"
                f"{daemon_output(log_path)}"
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
        f"{daemon_output(log_path)}"
    )


__all__ = [
    "BUNDLED_REFERENCE_SPEAKER",
    "DEFAULT_TTS_MODEL_PATH",
    "DaemonHandle",
    "daemon_env",
    "daemon_output",
    "combined_llama_env_overrides",
    "llm_artifact_path",
    "llm_request_payload",
    "post_json",
    "started_daemon",
    "tts_model_path",
    "visible_digits",
    "visible_llm_message",
    "wait_for_log_text",
]