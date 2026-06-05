"""Functional end-to-end STT test using the real daemon."""

from __future__ import annotations

import json
import socket
import urllib.error
import urllib.request
from pathlib import Path
from uuid import uuid4

import pytest

from llm_functional_support import BUNDLED_REFERENCE_SPEAKER
from llm_functional_support import daemon_env
from llm_functional_support import post_json
from llm_functional_support import started_daemon

from airunner_services.runtimes.faster_whisper_stt_executor import (
    discover_model_path,
)


def _free_tcp_port() -> int:
    """Return one free local TCP port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _multipart_audio_body(
    boundary: str,
    audio_path: Path,
    *,
    mime_type: str,
) -> bytes:
    """Encode one multipart audio upload body."""
    payload = audio_path.read_bytes()
    header = (
        f"--{boundary}\r\n"
        "Content-Disposition: form-data; "
        f'name="audio"; filename="{audio_path.name}"\r\n'
        f"Content-Type: {mime_type}\r\n\r\n"
    ).encode("utf-8")
    return b"".join(
        [header, payload, b"\r\n", f"--{boundary}--\r\n".encode("utf-8")]
    )


def _post_audio(
    url: str,
    audio_path: Path,
    *,
    mime_type: str = "audio/wav",
    timeout_seconds: float = 300.0,
) -> tuple[int, bytes, str]:
    """POST one multipart audio upload and return status, body, type."""
    boundary = f"airunner-stt-{uuid4().hex}"
    request = urllib.request.Request(
        url,
        data=_multipart_audio_body(
            boundary,
            audio_path,
            mime_type=mime_type,
        ),
        headers={
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "Accept": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(
            request, timeout=timeout_seconds
        ) as response:
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
        return int(response.status), json.loads(
            response.read().decode("utf-8")
        )


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.timeout(1200)
def test_whisper_transcribe_end_to_end_without_gui_or_llm() -> None:
    """Load faster-whisper and transcribe bundled audio through the API."""
    if not BUNDLED_REFERENCE_SPEAKER.is_file():
        pytest.fail(
            "Bundled Bob Ross audio fixture is missing: "
            f"{BUNDLED_REFERENCE_SPEAKER}"
        )

    model_path = discover_model_path()
    if not model_path:
        pytest.skip(
            "Real faster-whisper model required; "
            "set AIRUNNER_WHISPER_MODEL_PATH or install one "
            "under ~/.local/share/airunner/text/models/stt"
        )

    model_path = Path(model_path).expanduser().resolve()
    if not model_path.exists():
        pytest.skip(f"Configured STT model is missing: {model_path}")

    with started_daemon(
        daemon_env(
            llm_on=False,
            tts_on=False,
            extra_env={
                "AIRUNNER_STT_ON": "1",
                "AIRUNNER_DISABLE_ALWAYS_TOOLS": "1",
                "AIRUNNER_WHISPER_MODEL_PATH": str(model_path),
                "AIRUNNER_WHISPER_HOST": "127.0.0.1",
                "AIRUNNER_WHISPER_PORT": str(_free_tcp_port()),
                "AIRUNNER_WHISPER_STARTUP_TIMEOUT": "120",
            },
        )
    ) as daemon:
        load_status, load_body, _ = post_json(
            f"{daemon.base_url}/api/v1/daemon/runtimes/stt/load",
            {
                "provider": "local",
                "deployment_mode": "sidecar",
                "request_id": "functional-stt-load",
            },
            timeout_seconds=180.0,
        )
        assert (
            load_status < 400
        ), f"STT load failed: {load_body.decode('utf-8', errors='replace')}"

        audio_file = BUNDLED_REFERENCE_SPEAKER
        status, body, content_type = _post_audio(
            f"{daemon.base_url}/api/v1/stt/transcribe",
            audio_file,
            mime_type="audio/wav",
            timeout_seconds=300.0,
        )
        assert (
            status < 400
        ), f"STT transcription failed: {body.decode('utf-8', errors='replace')}"
        response = json.loads(body.decode("utf-8"))
        text = response.get("text", "")
        assert text, "Expected non-empty transcription text"


__all__ = [
    "test_whisper_transcribe_end_to_end_without_gui_or_llm",
]
