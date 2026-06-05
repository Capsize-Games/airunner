"""Integration tests for RPC dispatch infrastructure."""

import pytest
from airunner_services.api.routes.events import (
    _rpc_routes,
    _dispatch_rpc,
    _path_to_regex,
)


def test_path_to_regex_literal():
    pattern, params = _path_to_regex("/api/v1/health")
    assert pattern.match("/api/v1/health") is not None
    assert params == []


def test_path_to_regex_with_params():
    pattern, params = _path_to_regex("/api/v1/settings/resources/{name}/singleton")
    match = pattern.match("/api/v1/settings/resources/myres/singleton")
    assert match is not None
    assert params == ["name"]


def test_path_to_regex_multiple_params():
    pattern, params = _path_to_regex("/api/v1/art/images/{date}/info/{filename}")
    match = pattern.match("/api/v1/art/images/20240601/info/test.png")
    assert match is not None
    assert params == ["date", "filename"]


def test_path_to_regex_no_match():
    pattern, _ = _path_to_regex("/api/v1/health")
    assert pattern.match("/api/v1/nonexistent") is None


@pytest.mark.asyncio
async def test_dispatch_health_route():
    result = await _dispatch_rpc("GET", "/api/v1/health", {}, None)
    assert result["status"] == 200


@pytest.mark.asyncio
async def test_dispatch_404():
    result = await _dispatch_rpc("GET", "/api/v1/nonexistent", {}, None)
    assert result["status"] == 404


def test_all_routes_registered():
    registered: set[tuple[str, str]] = set()
    for method, pattern, _params, _func in _rpc_routes:
        registered.add((method, pattern.pattern))

    required = [
        ("GET", "/api/v1/health"),
        ("GET", "/api/v1/models/active"),
        ("GET", "/api/v1/knowledge-base/documents"),
        ("GET", "/api/v1/art/options"),
        ("GET", "/api/v1/art/bootstrap"),
        ("GET", "/api/v1/llm/conversations"),
        ("GET", "/api/v1/art/images/dates"),
        ("POST", "/api/v1/downloads/huggingface"),
        ("POST", "/api/v1/downloads/civitai/models"),
        ("GET", "/api/v1/art/loras"),
        ("GET", "/api/v1/art/embeddings"),
    ]

    for method, path in required:
        target_pat, _ = _path_to_regex(path)
        found = any(
            r_method == method and r_pat == target_pat.pattern
            for r_method, r_pat in registered
        )
        assert found, f"Route {method} {path} not registered"
