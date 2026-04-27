"""Tests for daemon lifecycle ownership."""

from pathlib import Path
from types import SimpleNamespace

from airunner.runtimes.contracts import RuntimeKind
from airunner.runtimes.registry import RuntimeRoute


def _daemon_config():
    return SimpleNamespace(
        config={"logging": {}, "models": {}, "health": {}, "server": {}},
        config_path=Path("/tmp/daemon.yaml"),
    )


def test_daemon_owns_headless_lifecycle(monkeypatch):
    import airunner.services.daemon as daemon_module

    calls = []

    class FakeLifecycleService:
        def initialize(self):
            calls.append("initialize")

        def preload_llm_model(self):
            calls.append("preload")

    class FakeApp:
        def __init__(self, **kwargs):
            calls.append(("app", kwargs))
            self.lifecycle_service = FakeLifecycleService()

        def ensure_lifecycle_service(self):
            return self.lifecycle_service

    monkeypatch.setattr(
        daemon_module.AIRunnerDaemon,
        "_setup_logging",
        lambda self: None,
    )
    monkeypatch.setattr(
        daemon_module.AIRunnerDaemon,
        "_setup_signal_handlers",
        lambda self: None,
    )
    monkeypatch.setattr(daemon_module, "App", FakeApp)
    monkeypatch.setattr(
        daemon_module.AIRunnerDaemon,
        "_start_health_monitor",
        lambda self: calls.append("health"),
    )
    monkeypatch.setattr(
        daemon_module.AIRunnerDaemon,
        "_start_api_server",
        lambda self: calls.append("api"),
    )
    monkeypatch.setattr(
        daemon_module.AIRunnerDaemon,
        "_run_loop",
        lambda self: calls.append("loop"),
    )
    monkeypatch.setattr(
        daemon_module.AIRunnerDaemon,
        "_preload_models",
        lambda self: calls.append("config-preload"),
    )

    daemon = daemon_module.AIRunnerDaemon(_daemon_config())
    daemon.start()

    app_kwargs = calls[0][1]
    assert app_kwargs["headless"] is True
    assert app_kwargs["start_headless_api_server"] is False
    assert app_kwargs["initialize_headless_lifecycle"] is False
    assert calls[1:] == [
        "initialize",
        "preload",
        "config-preload",
        "health",
        "api",
        "loop",
    ]


def test_daemon_shutdown_closes_runtime_clients(monkeypatch):
    import airunner.services.daemon as daemon_module

    calls = []

    class FakeClient:
        def close(self):
            calls.append("close")

    class FakeRegistry:
        def __init__(self, client):
            self.client = client

        def list_routes(self):
            return (
                RuntimeRoute(RuntimeKind.LLM, provider="local"),
                RuntimeRoute(
                    RuntimeKind.LLM,
                    provider="local",
                    deployment_mode="sidecar",
                ),
            )

        def resolve(self, runtime, provider, deployment_mode):
            return self.client

    monkeypatch.setattr(
        daemon_module.AIRunnerDaemon,
        "_setup_logging",
        lambda self: None,
    )
    monkeypatch.setattr(
        daemon_module.AIRunnerDaemon,
        "_setup_signal_handlers",
        lambda self: None,
    )
    monkeypatch.setattr(
        daemon_module.sys,
        "exit",
        lambda code: calls.append(code),
    )

    daemon = daemon_module.AIRunnerDaemon(_daemon_config())
    daemon.app = SimpleNamespace(
        runtime_registry=FakeRegistry(FakeClient()),
        cleanup=lambda: calls.append("cleanup"),
    )
    daemon.shutdown()

    assert calls == ["close", "cleanup", 0]
