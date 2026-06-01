"""Smoke tests for the service-owned daemon API bootstrap.

Verifies that the API server can be constructed and the FastAPI app
registers all expected routes without runtime model dependencies.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest


# Ensure the services/src and native/src directories
# are on the path for the service-owned API imports.
_SERVICES_ROOT = Path(__file__).resolve().parents[1]
_PROJECT_ROOT = _SERVICES_ROOT.parent
_SERVICES_SRC = _PROJECT_ROOT / "services" / "src"
_NATIVE_SRC = _PROJECT_ROOT / "native" / "src"

# Append paths (not prepend) to avoid shadowing site-packages.
# The services/src directory contains a 'requests/' package that would
# shadow the real requests library if placed earlier in sys.path.
for _path in (_SERVICES_SRC, _NATIVE_SRC):
    _path_str = str(_path)
    if _path_str not in sys.path:
        sys.path.append(_path_str)


class TestImportChain:
    """Verify that the service-owned API modules resolve."""

    def test_deleted_api_package_not_importable(self):
        """The removed top-level api package stays absent."""
        assert importlib.util.find_spec("airunner_api") is None

    def test_service_message_envelopes_are_self_owned(self):
        """Services resolve runtime envelope classes from their own module."""
        from airunner_services.ipc.messages import EnvelopeStatus as ServiceStatus
        from airunner_services.runtimes.message_envelopes import (
            load_message_types,
        )

        assert ServiceStatus is load_message_types().EnvelopeStatus

    def test_import_service_api_server(self):
        """The service-owned API server module resolves."""
        import airunner_services.api.server  # noqa: F401

    def test_import_service_api_routes_health(self):
        """Health route module resolves."""
        import airunner_services.api.routes.health  # noqa: F401

    def test_import_service_api_routes_art(self):
        """Art route module resolves."""
        import airunner_services.api.routes.art  # noqa: F401

    def test_import_service_api_routes_llm(self):
        """LLM route module resolves."""
        import airunner_services.api.routes.llm  # noqa: F401

    def test_import_service_api_routes_tts(self):
        """TTS route module resolves."""
        import airunner_services.api.routes.tts  # noqa: F401

    def test_import_service_api_routes_stt(self):
        """STT route module resolves."""
        import airunner_services.api.routes.stt  # noqa: F401

    def test_import_service_api_routes_daemon(self):
        """Daemon route module resolves."""
        import airunner_services.api.routes.daemon  # noqa: F401

    def test_import_service_api_routes_downloads(self):
        """Downloads route module resolves."""
        import airunner_services.api.routes.downloads  # noqa: F401

    def test_import_service_api_routes_conversations(self):
        """Conversations route module resolves."""
        import airunner_services.api.routes.conversations  # noqa: F401


class TestFastAPIAppConstruction:
    """Verify that the FastAPI application can be constructed."""

    def test_create_app_returns_fastapi_instance(self):
        """create_app() returns a FastAPI application."""
        from airunner_services.api.server import create_app

        app = create_app(
            allowed_origins=["http://localhost"],
            enable_cors=True,
        )
        assert app is not None
        assert app.title == "AI Runner API"

    def test_all_expected_routes_registered(self):
        """The FastAPI app registers all expected route prefixes."""
        from airunner_services.api.server import create_app

        app = create_app(
            allowed_origins=["http://localhost"],
            enable_cors=True,
        )

        routes = {route.path for route in app.routes if hasattr(route, "path")}

        expected_prefixes = [
            "/api/v1/health",
            "/api/v1/daemon",
            "/api/v1/llm",
            "/api/v1/art",
            "/api/v1/tts",
            "/api/v1/stt",
            "/api/v1/downloads",
            "/api/v1/persistence",
        ]

        for prefix in expected_prefixes:
            found = any(route.startswith(prefix) for route in routes)
            assert found, f"Route prefix {prefix} not found in {sorted(routes)}"

    def test_root_endpoint(self, monkeypatch):
        """The root endpoint returns service info."""
        from airunner_services.api.server import create_app
        from fastapi.testclient import TestClient

        monkeypatch.setenv("AIRUNNER_INSECURE_NO_AUTH", "1")
        app = create_app(
            allowed_origins=["http://localhost"],
            enable_cors=True,
        )
        client = TestClient(app)
        response = client.get("/")
        assert response.status_code == 200
        body = response.json()
        # The root response may use either "status" or "message" key
        # depending on which router handles the root path
        assert body.get("status") == "ready" or "AI Runner" in str(body)
