"""Happy/sad/hostile contracts for the image-generation MCP server."""

from __future__ import annotations

import asyncio
import base64
from pathlib import Path
from typing import Any

import httpx
import pytest

from airunner_services.mcp.config import MCPConfig, _parse_bool
from airunner_services.mcp.daemon_client import ArtDaemonClient, DaemonError
from airunner_services.mcp.daemon_client import is_loopback_url
from airunner_services.mcp.payloads import build_generation_payload
from airunner_services.mcp.server import build_server
from airunner_services.mcp.server import fetch_result, run_generation
from airunner_services.mcp.server import run_background_removal

_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8"
    "z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)


def _config(tmp_path: Path, **overrides: Any) -> MCPConfig:
    """Return a test config writing images under tmp_path."""
    return MCPConfig(
        daemon_url="http://127.0.0.1:8080",
        output_dir=str(tmp_path),
        poll_interval_s=0.0,
        **overrides,
    )


def _client(
    handler: Any, tmp_path: Path, **overrides: Any
) -> ArtDaemonClient:
    """Return a client backed by a mock HTTP transport."""
    transport = httpx.MockTransport(handler)
    return ArtDaemonClient(_config(tmp_path, **overrides), transport)


def _ok_handler(request: httpx.Request) -> httpx.Response:
    """Serve a full successful generation round-trip."""
    path = request.url.path
    if path == "/api/v1/art/generate":
        return httpx.Response(200, json={"job_id": "job-1"})
    if path == "/api/v1/art/status/job-1":
        body = {"job_id": "job-1", "status": "completed", "image_count": 2}
        return httpx.Response(200, json=body)
    if path in ("/api/v1/art/result/job-1/0", "/api/v1/art/result/job-1/1"):
        return httpx.Response(200, content=_PNG)
    if path == "/api/v1/art/cancel/job-1":
        return httpx.Response(200, json={"status": "cancelled"})
    if path == "/api/v1/art/models":
        return httpx.Response(200, json={"models": []})
    if path == "/api/v1/art/models/registry":
        return httpx.Response(200, json=[])
    return httpx.Response(404, text="nope")


def test_payload_defaults_target_zimage_turbo() -> None:
    """Happy: defaults match the Z-Image Turbo sweet spot."""
    payload = build_generation_payload("a lighthouse at dusk")
    assert payload["steps"] == 9
    assert payload["cfg_scale"] == 0.0
    assert payload["provider"] == "local"
    assert payload["width"] == 1024


def test_payload_rejects_blank_and_oversize_prompt() -> None:
    """Hostile: blank or oversize prompts fail before any HTTP call."""
    for bad in ("", "   ", "x" * 4001):
        with pytest.raises(ValueError):
            build_generation_payload(bad)


def test_payload_rejects_out_of_bounds_options() -> None:
    """Hostile: each out-of-bounds option raises ValueError."""
    bad_options: list[dict[str, Any]] = [
        {"width": 0},
        {"height": 99999},
        {"steps": 0},
        {"cfg_scale": -0.5},
        {"num_images": 9},
        {"seed": -1},
        {"strength": 1.5},
        {"provider": "openai"},
    ]
    for options in bad_options:
        with pytest.raises(ValueError):
            build_generation_payload("ok", **options)


def test_payload_rejects_missing_input_image(tmp_path: Path) -> None:
    """Hostile: img2img with no file fails locally, not at the daemon."""
    missing = str(tmp_path / "nope.png")
    with pytest.raises(ValueError):
        build_generation_payload("ok", input_image_path=missing)


def test_generate_end_to_end_saves_pngs(tmp_path: Path) -> None:
    """Happy: run_generation waits, saves, and returns images."""
    client = _client(_ok_handler, tmp_path)
    payload = build_generation_payload("a lighthouse", num_images=2)
    outcome = run_generation(client, _config(tmp_path), payload)
    summary = outcome[0]
    assert summary["job_id"] == "job-1"
    assert summary["image_count"] == 2
    for path in summary["files"]:
        assert Path(path).read_bytes() == _PNG
    assert len(outcome) == 3


def test_fetch_result_returns_saved_image(tmp_path: Path) -> None:
    """Happy: fetch_result downloads one batch image to disk."""
    client = _client(_ok_handler, tmp_path)
    outcome = fetch_result(client, _config(tmp_path), "job-1", 1)
    assert outcome[0]["file"].endswith("job-1-1.png")
    assert Path(outcome[0]["file"]).read_bytes() == _PNG


def test_cancel_and_list_models(tmp_path: Path) -> None:
    """Happy: cancel and model listing pass daemon payloads through."""
    client = _client(_ok_handler, tmp_path)
    assert client.cancel_job("job-1")["status"] == "cancelled"
    assert client.list_models() == {"models": []}
    assert client.list_registry_models() == []


def test_start_capacity_error_surfaces_status(tmp_path: Path) -> None:
    """Sad: a full daemon (503) raises with the status attached."""
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, text="capacity full")

    with pytest.raises(DaemonError) as caught:
        _client(handler, tmp_path).start_generation({"prompt": "x"})
    assert caught.value.status_code == 503


def test_failed_job_raises_with_reason(tmp_path: Path) -> None:
    """Sad: a failed job raises instead of returning images."""
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("generate"):
            return httpx.Response(200, json={"job_id": "job-9"})
        body = {"job_id": "job-9", "status": "failed", "error": "boom"}
        return httpx.Response(200, json=body)

    client = _client(handler, tmp_path)
    with pytest.raises(DaemonError, match="failed"):
        client.wait_for_completion("job-9")


def test_wait_timeout_raises(tmp_path: Path) -> None:
    """Sad: a never-finishing job hits the configured timeout."""
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"status": "running"})

    client = _client(handler, tmp_path, generation_timeout_s=0.01)
    with pytest.raises(DaemonError, match="timed out"):
        client.wait_for_completion("job-1")


def test_job_id_traversal_rejected_without_http() -> None:
    """Hostile: path-like job ids never reach the network."""
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, json={})

    client = _client(handler, Path("/tmp"))
    for bad in ("", "../secret", "a/b", "a\\b"):
        with pytest.raises(DaemonError):
            client.get_status(bad)
    assert calls == []


def test_remove_background_end_to_end_saves_png(tmp_path: Path) -> None:
    """Happy: background removal saves the RGBA PNG and returns it."""
    source = tmp_path / "cat.png"
    source.write_bytes(_PNG)

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/v1/art/remove-background"
        return httpx.Response(200, content=_PNG)

    client = _client(handler, tmp_path)
    outcome = run_background_removal(client, _config(tmp_path), str(source))
    assert outcome[0]["file"].endswith("cat-nobg.png")
    assert Path(outcome[0]["file"]).read_bytes() == _PNG
    assert len(outcome) == 2


def test_remove_background_missing_input_file(tmp_path: Path) -> None:
    """Hostile: a missing input fails locally, not at the daemon."""
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, content=_PNG)

    client = _client(handler, tmp_path)
    with pytest.raises(ValueError):
        run_background_removal(client, _config(tmp_path), str(tmp_path))
    assert calls == []


def test_remove_background_daemon_error(tmp_path: Path) -> None:
    """Sad: a daemon failure raises with the status attached."""
    source = tmp_path / "cat.png"
    source.write_bytes(_PNG)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="rmbg exploded")

    client = _client(handler, tmp_path)
    with pytest.raises(DaemonError) as caught:
        run_background_removal(client, _config(tmp_path), str(source))
    assert caught.value.status_code == 500


def test_server_registers_six_tools(tmp_path: Path) -> None:
    """Happy: the MCP server exposes the generation tool surface."""
    client = _client(_ok_handler, tmp_path)
    server = build_server(_config(tmp_path), client)
    tools = asyncio.run(server.list_tools())
    names = sorted(tool.name for tool in tools)
    assert names == [
        "cancel_generation",
        "fetch_generation_result",
        "generate_image",
        "get_generation_status",
        "list_image_models",
        "remove_background",
    ]


def test_config_from_env_overrides(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Happy: env vars override daemon URL, key, and timeouts."""
    monkeypatch.setenv("AIRUNNER_DAEMON_URL", "http://10.0.0.2:9999/")
    monkeypatch.setenv("AIRUNNER_API_KEY", "secret")
    monkeypatch.setenv("AIRUNNER_MCP_GENERATION_TIMEOUT_S", "42")
    config = MCPConfig.from_env()
    assert config.daemon_url == "http://10.0.0.2:9999"
    assert config.api_key == "secret"
    assert config.generation_timeout_s == 42.0


class _FakeLauncher:
    """Daemon launcher double recording start calls."""

    def __init__(self) -> None:
        """Track how many times the client starts the daemon."""
        self.starts = 0

    def start(self) -> None:
        """Record one daemon start without spawning a process."""
        self.starts += 1


def _autostart_client(
    tmp_path: Path,
    handler: Any,
    launcher: _FakeLauncher,
    **overrides: Any,
) -> ArtDaemonClient:
    """Return a client wired to a mock transport and fake launcher."""
    transport = httpx.MockTransport(handler)
    return ArtDaemonClient(
        _config(tmp_path, **overrides),
        transport,
        lambda: launcher,
    )


def test_is_loopback_url_only_matches_this_host() -> None:
    """Happy: only loopback daemon URLs qualify for auto-start."""
    assert is_loopback_url("http://127.0.0.1:8080") is True
    assert is_loopback_url("http://localhost:8080/health") is True
    assert is_loopback_url("http://192.168.1.10:8080") is False
    assert is_loopback_url("http://example.com:8080") is False
    assert is_loopback_url("not a url") is False


def test_autostart_launches_daemon_and_retries(
    tmp_path: Path,
) -> None:
    """Happy: a down daemon is started, then the job runs."""
    launcher = _FakeLauncher()

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if launcher.starts == 0:
            raise httpx.ConnectError("daemon is not running")
        if path == "/health":
            return httpx.Response(200, json={"status": "ok"})
        if path == "/api/v1/art/generate":
            return httpx.Response(200, json={"job_id": "job-1"})
        if path == "/api/v1/art/status/job-1":
            body = {"job_id": "job-1", "status": "completed"}
            return httpx.Response(200, json={**body, "image_count": 1})
        if path == "/api/v1/art/result/job-1/0":
            return httpx.Response(200, content=_PNG)
        return httpx.Response(404, text="nope")

    client = _autostart_client(tmp_path, handler, launcher)
    payload = build_generation_payload("a lighthouse")
    outcome = run_generation(client, _config(tmp_path), payload)
    summary = outcome[0]
    assert summary["job_id"] == "job-1"
    assert launcher.starts == 1
    assert Path(summary["files"][0]).read_bytes() == _PNG


def test_autostart_skipped_when_daemon_already_up(
    tmp_path: Path,
) -> None:
    """Happy: a reachable daemon is used as-is with no launch."""
    launcher = _FakeLauncher()

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/v1/art/models":
            return httpx.Response(200, json={"models": []})
        return httpx.Response(404, text="nope")

    client = _autostart_client(tmp_path, handler, launcher)
    client.ensure_daemon_running()

    assert launcher.starts == 0
    assert client.list_models() == {"models": []}
    assert launcher.starts == 0


def test_autostart_disabled_raises_without_launch(
    tmp_path: Path,
) -> None:
    """Sad: opt-out keeps the unreachable error and starts nothing."""
    launcher = _FakeLauncher()

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("daemon is not running")

    client = _autostart_client(
        tmp_path, handler, launcher, auto_start_daemon=False
    )
    with pytest.raises(DaemonError, match="daemon unreachable"):
        client.list_models()

    assert launcher.starts == 0


def test_autostart_refuses_non_loopback_url(
    tmp_path: Path,
) -> None:
    """Hostile: a remote daemon URL is never auto-started locally."""
    launcher = _FakeLauncher()

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("daemon is not running")

    transport = httpx.MockTransport(handler)
    client = ArtDaemonClient(
        MCPConfig(
            daemon_url="http://192.168.1.10:8080",
            output_dir=str(tmp_path),
            poll_interval_s=0.0,
        ),
        transport,
        lambda: launcher,
    )
    with pytest.raises(DaemonError, match="daemon unreachable"):
        client.list_models()

    assert launcher.starts == 0


def test_autostart_failure_surfaces_launch_error(
    tmp_path: Path,
) -> None:
    """Sad: a launcher failure raises instead of retrying forever."""

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("daemon is not running")

    transport = httpx.MockTransport(handler)
    client = ArtDaemonClient(_config(tmp_path), transport)
    client._launcher_factory = lambda: _FailingLauncher()
    with pytest.raises(DaemonError, match="auto-start failed"):
        client.list_models()


class _FailingLauncher:
    """Launcher double whose start always fails."""

    def start(self) -> None:
        """Raise instead of spawning a daemon process."""
        raise OSError("no daemon binary")


def test_config_from_env_autostart_overrides(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Happy: env vars toggle auto-start and its startup timeout."""
    monkeypatch.setenv("AIRUNNER_MCP_AUTO_START_DAEMON", "0")
    monkeypatch.setenv("AIRUNNER_MCP_DAEMON_STARTUP_TIMEOUT_S", "12")
    config = MCPConfig.from_env()
    assert config.auto_start_daemon is False
    assert config.daemon_startup_timeout_s == 12.0


def test_read_timeout_does_not_autostart_or_retry(
    tmp_path: Path,
) -> None:
    """Sad: a busy daemon timeout surfaces with no launch or retry."""
    launcher = _FakeLauncher()
    posts: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/health":
            return httpx.Response(200, json={"status": "ok"})
        if request.url.path == "/api/v1/art/generate":
            posts.append(request)
            raise httpx.ReadTimeout("daemon busy")
        return httpx.Response(404, text="nope")

    client = _autostart_client(tmp_path, handler, launcher)
    with pytest.raises(DaemonError, match="daemon unreachable"):
        client.start_generation({"prompt": "x"})

    assert launcher.starts == 0
    assert len(posts) == 1


def test_config_unrecognized_bool_falls_back_to_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Sad: an unrecognized boolean env value keeps the default."""
    monkeypatch.setenv("AIRUNNER_MCP_AUTO_START_DAEMON", "sometimes")
    config = MCPConfig.from_env()
    assert config.auto_start_daemon is True
    assert _parse_bool("sometimes", True) is True
    assert _parse_bool("sometimes", False) is False
    assert _parse_bool("yes", False) is True
    assert _parse_bool("off", True) is False
