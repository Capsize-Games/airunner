"""Bootstrap gate tests for the optional Muse art route."""

from __future__ import annotations

import sys
import types
from typing import Any

import pytest

from airunner_services.runtimes.bootstrap import (
    build_runtime_registry,
    muse_art_enabled,
)
from airunner_services.runtimes.contracts import RuntimeKind
from airunner_services.runtimes.registry import (
    RuntimeRegistry,
    RuntimeRoute,
)

_MODULE = "airunner_services.runtimes.muse_art_client"
_KEY = "MODEL_API_KEY"


def _fake_muse_module() -> types.ModuleType:
    module = types.ModuleType(_MODULE)

    class FakeMuseArtClient:
        """Stand-in for the W1 Muse client class."""

    def register(
        registry: RuntimeRegistry,
        client: Any = None,
    ) -> RuntimeRegistry:
        route = RuntimeRoute(
            RuntimeKind.ART, provider="muse", deployment_mode="cloud"
        )
        registry.register(route, client or FakeMuseArtClient())
        return registry

    setattr(module, "MuseArtClient", FakeMuseArtClient)
    setattr(module, "register_muse_art_client", register)
    return module


def _has_muse_route(registry: RuntimeRegistry) -> bool:
    return any(
        route.runtime is RuntimeKind.ART and route.provider == "muse"
        for route in registry.list_routes()
    )


def _muse_route(registry: RuntimeRegistry) -> RuntimeRoute:
    for route in registry.list_routes():
        if route.provider == "muse":
            return route
    raise AssertionError("muse route missing")


def test_predicate_true_only_for_nonblank_key() -> None:
    assert muse_art_enabled({_KEY: "secret"}) is True
    assert muse_art_enabled({_KEY: "  secret  "}) is True
    assert muse_art_enabled({}) is False
    assert muse_art_enabled({_KEY: ""}) is False
    assert muse_art_enabled({_KEY: "   "}) is False


def test_without_key_muse_route_absent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(_KEY, raising=False)
    monkeypatch.setitem(sys.modules, _MODULE, _fake_muse_module())
    registry = build_runtime_registry()
    assert _has_muse_route(registry) is False


def test_with_key_muse_route_present_cloud(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(_KEY, "test-key-not-logged")
    monkeypatch.setitem(sys.modules, _MODULE, _fake_muse_module())
    registry = build_runtime_registry()
    assert _has_muse_route(registry) is True
    assert _muse_route(registry).deployment_mode == "cloud"


def test_blank_key_muse_route_absent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(_KEY, "   ")
    monkeypatch.setitem(sys.modules, _MODULE, _fake_muse_module())
    registry = build_runtime_registry()
    assert _has_muse_route(registry) is False


def test_key_without_client_module_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(_KEY, "test-key-not-logged")
    monkeypatch.setitem(sys.modules, _MODULE, None)
    registry = build_runtime_registry()
    assert _has_muse_route(registry) is False


def test_local_routes_survive_gate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(_KEY, raising=False)
    registry = build_runtime_registry()
    providers = {route.provider for route in registry.list_routes()}
    assert "local" in providers
