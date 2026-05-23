"""Tests for the legacy server's service-app registry."""

from types import SimpleNamespace

from airunner_services.api import legacy_server
from airunner_services.utils.application import api_reference


def test_get_api_creates_one_service_app(monkeypatch) -> None:
    """get_api should create and cache one service-owned app."""
    created: list[str] = []
    sentinel = SimpleNamespace(name="service-app")

    def fake_create_api_app() -> SimpleNamespace:
        created.append("created")
        return sentinel

    monkeypatch.setattr(legacy_server, "_api", None)
    monkeypatch.setattr(
        legacy_server,
        "_create_api_app",
        fake_create_api_app,
    )

    assert legacy_server.get_api() is sentinel
    assert legacy_server.get_api() is sentinel
    assert created == ["created"]


def test_set_api_registers_existing_service_app(monkeypatch) -> None:
    """set_api should expose one pre-built app through get_api."""
    sentinel = SimpleNamespace(name="registered-app")

    monkeypatch.setattr(legacy_server, "_api", None)
    legacy_server.set_api(sentinel)

    assert legacy_server.get_api(create_if_missing=False) is sentinel


def test_api_reference_helpers_reuse_registered_service_app(
    monkeypatch,
) -> None:
    """API reference helpers should resolve the registered service app."""
    sentinel = SimpleNamespace(name="registered-app")

    monkeypatch.setattr(legacy_server, "_api", sentinel)

    assert api_reference.peek_registered_api() is sentinel
    assert api_reference.resolve_live_api_reference() is sentinel
    assert api_reference.api_from_qt_application() is sentinel