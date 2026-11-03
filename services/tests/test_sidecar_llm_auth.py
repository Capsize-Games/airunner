"""Private child credentials and sidecar request authentication tests."""

from __future__ import annotations

import http.server
import os
import stat
import threading
from pathlib import Path
from types import SimpleNamespace

import pytest

from airunner_services.api import loopback_token
from airunner_services.runtimes import sidecar_launcher
from airunner_services.runtimes.contracts import ChatMessage, LLMInvocationRequest
from airunner_services.runtimes.contracts import RuntimeAction, RuntimeKind
from airunner_services.runtimes.llama_cpp_runtime_settings import (
    LlamaCppRuntimeSettings,
)
from airunner_services.runtimes.sidecar_launcher import SidecarLauncher
from airunner_services.runtimes.sidecar_llm_client import SidecarLLMClient


class _HealthResponse:
    status = 200

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        pass


class _Process:
    def poll(self):
        return None

    def terminate(self):
        pass

    def wait(self, timeout=None):
        return None

    def kill(self):
        pass


def _settings(model_path: Path) -> LlamaCppRuntimeSettings:
    return LlamaCppRuntimeSettings(
        executable="llama-server",
        host="127.0.0.1",
        port=18081,
        model_path=str(model_path),
        model_id="test-model",
        runtime_profile="default",
        n_ctx=4096,
        n_gpu_layers=0,
        startup_timeout_seconds=1,
    )


def test_launcher_command_is_pure_and_start_provisions_private_token(
    tmp_path, monkeypatch
):
    token_file = tmp_path / "config" / "loopback_token"
    monkeypatch.setattr(loopback_token, "loopback_token_path", lambda: token_file)
    monkeypatch.setattr(sidecar_launcher, "loopback_token_path", lambda: token_file)
    monkeypatch.setattr(loopback_token, "_cached_token", None)
    monkeypatch.setattr(loopback_token, "_cache_loaded", False)
    model_path = tmp_path / "model.gguf"
    model_path.write_bytes(b"fixture")
    argv = []

    launcher = SidecarLauncher(
        _settings(model_path),
        process_factory=lambda command, **_kwargs: (argv.extend(command), _Process())[1],
        health_opener=lambda *_args, **_kwargs: _HealthResponse(),
        sleep=lambda _seconds: None,
        time_fn=lambda: 0.0,
    )
    command = launcher.command()
    assert not token_file.exists()
    assert command[command.index("--api-key-file") + 1] == str(token_file)
    status_client = SidecarLLMClient(
        settings=_settings(model_path), launcher=launcher
    )
    status_client.invoke(
        SimpleNamespace(
            runtime=RuntimeKind.LLM,
            action=RuntimeAction.STATUS,
            request_id="status-only",
        )
    )
    assert not token_file.exists()

    launcher.start()

    mode = stat.S_IMODE(token_file.stat().st_mode)
    token = token_file.read_text(encoding="utf-8").strip()
    assert mode == 0o600
    assert token
    assert token not in argv
    assert launcher.internal_auth_headers() == {
        "Authorization": f"Bearer {token}"
    }

    # A later actual start revalidates and tightens the existing file.
    os.chmod(token_file, 0o644)
    launcher.start()
    assert stat.S_IMODE(token_file.stat().st_mode) == 0o600


@pytest.mark.parametrize("provided", [None, "wrong-token", "expected-token"])
def test_internal_completion_requires_matching_bearer_token(provided):
    expected = "expected-token"
    seen_headers = []

    class AuthHandler(http.server.BaseHTTPRequestHandler):
        def do_POST(self):
            self.rfile.read(int(self.headers.get("Content-Length", "0")))
            authorization = self.headers.get("Authorization")
            seen_headers.append(authorization)
            if authorization != f"Bearer {expected}":
                body = b"internal credential rejected"
                self.send_response(401)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            body = (
                b'data: {"choices":[{"delta":{"content":"ok"},'
                b'"finish_reason":"stop"}]}\n\n'
                b"data: [DONE]\n\n"
            )
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *_args):
            pass

    class AuthLauncher:
        def __init__(self, endpoint):
            self.endpoint = endpoint

        def start(self):
            pass

        def stop(self):
            pass

        def internal_auth_headers(self):
            return (
                {"Authorization": f"Bearer {provided}"}
                if provided is not None
                else {}
            )

    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), AuthHandler)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    endpoint = f"http://127.0.0.1:{server.server_port}"
    settings = _settings(Path("/unused/model.gguf"))
    client = SidecarLLMClient(
        settings=settings,
        launcher=AuthLauncher(endpoint),
    )
    request = SimpleNamespace(
        runtime=RuntimeKind.LLM,
        action=RuntimeAction.INVOKE,
        request_id="auth-test",
        payload=LLMInvocationRequest(
            messages=[ChatMessage(role="user", content="hello")],
            stream=True,
        ).model_dump(),
    )
    try:
        deltas = list(client.stream(request))
    finally:
        server.shutdown()
        server.server_close()
        server_thread.join(2)

    assert len(seen_headers) == 1
    if provided == expected:
        assert seen_headers == [f"Bearer {expected}"]
        assert deltas[-1].final
        assert deltas[-1].status.value == "stream"
    else:
        assert seen_headers == [
            f"Bearer {provided}" if provided else None
        ]
        assert deltas[-1].final
        assert deltas[-1].status.value == "failed"
        assert "internal credential" not in deltas[-1].metadata["error"]
        assert expected not in deltas[-1].metadata["error"]
