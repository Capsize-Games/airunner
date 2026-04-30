"""Tests for daemon lifecycle ownership."""

import logging
from pathlib import Path
from types import SimpleNamespace

from airunner.runtimes.contracts import RuntimeKind
from airunner.runtimes.registry import RuntimeRoute


def _daemon_config():
    return SimpleNamespace(
        config={"logging": {}, "models": {}, "health": {}, "server": {}},
        config_path=Path("/tmp/daemon.yaml"),
    )


def test_configure_daemon_environment_sets_headless_defaults(monkeypatch):
    import airunner.services.daemon as daemon_module

    monkeypatch.delenv("AIRUNNER_HEADLESS", raising=False)
    monkeypatch.delenv("QT_QPA_PLATFORM", raising=False)
    monkeypatch.delenv("QT_LOGGING_RULES", raising=False)
    monkeypatch.delenv("PYTORCH_ALLOC_CONF", raising=False)
    monkeypatch.delenv("PYTORCH_CUDA_ALLOC_CONF", raising=False)

    daemon_module._configure_daemon_environment()

    assert daemon_module.os.environ["AIRUNNER_HEADLESS"] == "1"
    assert daemon_module.os.environ["QT_QPA_PLATFORM"] == "offscreen"
    assert (
        daemon_module.os.environ["QT_LOGGING_RULES"]
        == "*.debug=false;qt.qpa.*=false"
    )
    assert (
        daemon_module.os.environ["PYTORCH_ALLOC_CONF"]
        == "backend:cudaMallocAsync"
    )
    assert (
        daemon_module.os.environ["PYTORCH_CUDA_ALLOC_CONF"]
        == daemon_module.os.environ["PYTORCH_ALLOC_CONF"]
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


def test_daemon_logging_skips_file_output_by_default(monkeypatch):
    import airunner.services.daemon as daemon_module

    root_logger = logging.getLogger()
    original_handlers = list(root_logger.handlers)
    root_logger.handlers.clear()
    monkeypatch.delenv("AIRUNNER_SAVE_LOG_TO_FILE", raising=False)
    monkeypatch.setattr(
        daemon_module.AIRunnerDaemon,
        "_setup_signal_handlers",
        lambda self: None,
    )

    called = {"value": False}

    class FakeRotatingFileHandler:
        def __init__(self, *args, **kwargs):
            called["value"] = True

    monkeypatch.setattr(
        daemon_module,
        "RotatingFileHandler",
        FakeRotatingFileHandler,
    )

    try:
        daemon_module.AIRunnerDaemon(_daemon_config())
        assert called["value"] is False
    finally:
        root_logger.handlers.clear()
        root_logger.handlers.extend(original_handlers)
