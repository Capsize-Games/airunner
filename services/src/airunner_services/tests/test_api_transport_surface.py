"""Regression tests for the extracted API transport and client surfaces."""

from __future__ import annotations


def test_fastapi_adapter_surface_resolves_to_service_server() -> None:
    """The API transport adapter should expose the current FastAPI server."""
    from airunner_api.transport.fastapi import APIServer as APIAPIServer
    from airunner_api.transport.fastapi import create_app as api_create_app
    from airunner_services.api.server import APIServer
    from airunner_services.api.server import create_app

    assert APIAPIServer is APIServer
    assert api_create_app is create_app