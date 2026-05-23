import asyncio
from types import SimpleNamespace


def test_daemon_status_endpoint_reports_lifecycle_state():
    from airunner_api.routes.health import daemon_status

    status = {
        "lifecycle_initialized": True,
        "worker_manager_ready": True,
        "model_load_balancer_ready": True,
        "loaded_models": ["LLM"],
        "runtime_registry_ready": True,
        "embedded_api_server_running": False,
        "preloaded_model_path": "/models/qwen",
    }
    fake_request = SimpleNamespace(
        app=SimpleNamespace(
            state=SimpleNamespace(
                lifecycle_service=SimpleNamespace(get_status=lambda: status)
            )
        )
    )

    response = asyncio.run(daemon_status(fake_request))

    assert response.model_dump() == status