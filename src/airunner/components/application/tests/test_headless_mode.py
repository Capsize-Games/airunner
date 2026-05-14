"""Tests for non-launching headless lifecycle behavior."""

from pathlib import Path
from types import SimpleNamespace

from airunner.app import App
from airunner.enums import EngineResponseCode, SignalCode


class FakeLogger:
    def info(self, *args, **kwargs):
        return None


def _daemon_config():
    return SimpleNamespace(
        config={"logging": {}, "models": {}, "health": {}, "server": {}},
        config_path=Path("/tmp/daemon.yaml"),
    )


def test_daemon_creates_headless_app_without_embedded_server(monkeypatch):
    """Daemon headless bootstrap should disable embedded app server ownership."""
    import airunner.services.daemon as daemon_module

    captured = {}

    class FakeApp:
        def __init__(self, **kwargs):
            captured.update(kwargs)

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

    daemon = daemon_module.AIRunnerDaemon(_daemon_config())
    daemon._create_headless_app()

    assert captured["headless"] is True
    assert captured["no_splash"] is True
    assert captured["start_headless_api_server"] is False
    assert captured["initialize_headless_lifecycle"] is False


def test_lifecycle_status_does_not_require_app_bootstrap():
    """Lifecycle status should be inspectable without launching App."""
    from airunner.services.lifecycle_service import CoreLifecycleService

    signal_source = SimpleNamespace(
        logger=FakeLogger(),
        runtime_registry=None,
        api_server_thread=None,
        emit_signal=lambda code, data=None: None,
    )
    service = CoreLifecycleService(
        signal_source=signal_source,
        logger=signal_source.logger,
    )

    assert service.get_status() == {
        "lifecycle_initialized": False,
        "worker_manager_ready": False,
        "model_load_balancer_ready": False,
        "loaded_models": [],
        "runtime_registry_ready": False,
        "embedded_api_server_running": False,
        "preloaded_model_path": None,
    }


def test_headless_api_services_include_art_and_llm(monkeypatch):
    """Headless app compatibility services should include art and llm."""
    import airunner.app_mixins.headless_runtime_mixin as headless_module

    llm_service = object()
    art_service = object()
    host = SimpleNamespace()

    monkeypatch.setattr(
        headless_module,
        "LLMAPIService",
        lambda: llm_service,
    )
    monkeypatch.setattr(
        headless_module,
        "ARTAPIService",
        lambda: art_service,
    )

    headless_module.HeadlessRuntimeMixin._ensure_headless_api_services(host)

    assert host.llm is llm_service
    assert host.art is art_service


def test_headless_app_worker_response_emits_shared_signal():
    """Headless App should provide the worker-response API surface."""
    emitted = []
    host = SimpleNamespace(
        emit_signal=lambda code, data=None: emitted.append((code, data))
    )

    App.worker_response(
        host,
        EngineResponseCode.IMAGE_GENERATED,
        "ok",
    )

    assert emitted == [
        (
            SignalCode.ENGINE_RESPONSE_WORKER_RESPONSE_SIGNAL,
            {
                "code": EngineResponseCode.IMAGE_GENERATED,
                "message": "ok",
            },
        )
    ]


def test_headless_app_application_error_emits_status_signal():
    """Headless App should provide the shared application-error hook."""
    emitted = []
    logged = []
    host = SimpleNamespace(
        emit_signal=lambda code, data=None: emitted.append((code, data)),
        logger=SimpleNamespace(error=lambda message: logged.append(message)),
    )

    App.application_error(host, message="boom")

    assert logged == ["Application error emitted (message_chars=4)"]
    assert emitted == [
        (
            SignalCode.APPLICATION_STATUS_ERROR_SIGNAL,
            {"message": "boom"},
        )
    ]


def test_headless_app_application_settings_changed_emits_signal():
    """Headless App should provide the shared settings-changed hook."""
    emitted = []
    host = SimpleNamespace(
        emit_signal=lambda code, data=None: emitted.append((code, data))
    )

    App.application_settings_changed(
        host,
        setting_name="llm_generator_settings",
        column_name="current_conversation_id",
        val=77,
    )

    assert emitted == [
        (
            SignalCode.APPLICATION_SETTINGS_CHANGED_SIGNAL,
            {
                "setting_name": "llm_generator_settings",
                "column_name": "current_conversation_id",
                "val": 77,
            },
        )
    ]


def test_optional_extensions_disabled_in_art_sidecar(monkeypatch):
    """Art sidecar processes should skip optional extension scanning."""
    monkeypatch.setenv("AIRUNNER_ART_SIDECAR_PROCESS", "1")

    assert App._should_load_optional_extensions() is False


def test_optional_extensions_enabled_in_regular_app(monkeypatch):
    """Regular GUI and daemon processes should still load extensions."""
    monkeypatch.delenv("AIRUNNER_ART_SIDECAR_PROCESS", raising=False)

    assert App._should_load_optional_extensions() is True
