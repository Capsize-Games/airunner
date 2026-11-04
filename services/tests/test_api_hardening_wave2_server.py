"""Wave-2 API hardening: events, query codes, server policy, tenant.

Covers events RPC limit clamps, fixed persistence-query error codes,
CORS wildcard rejection, docs gating, the shared tenant allowlist
snapshot, and the LLM field allowlist.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from airunner_services.api import server as server_module
from airunner_services.api.routes.events_handlers import (
    _conversations,
    _parse_limit,
    _thread,
    _truncate,
)
from airunner_services.api.routes.legacy_llm_helpers import (
    build_llm_request,
)
from airunner_services.api.routes.persistence_contracts import (
    OrderClause,
    QueryCondition,
)
from airunner_services.api.routes.persistence_query import (
    apply_expressions,
    apply_order_by,
    expression_clause,
)
from airunner_services.api.routes.ws_auth import scope_websocket_tenant
from airunner_services.api.server import create_app
from airunner_services.data.tenant import (
    get_tenant_key,
    reset_tenant_key,
    set_tenant_key,
)


def _client(monkeypatch) -> TestClient:
    """Return a TestClient with auth disabled."""
    monkeypatch.setenv("AIRUNNER_API_KEY", "")
    monkeypatch.setenv("AIRUNNER_INSECURE_NO_AUTH", "1")
    return TestClient(
        create_app(
            allowed_origins=["http://localhost"], enable_cors=False
        )
    )


def test_events_limit_clamps() -> None:
    """Unparseable RPC limits are 400s; numerics clamp, never explode."""
    assert _parse_limit(None, 50, 200) == 50
    assert _parse_limit("999999", 50, 200) == 200
    assert _parse_limit("abc", 50, 200) is None
    code, _ = _conversations("", {"limit": "abc"})
    assert code == 400
    code, _ = _thread("/api/v1/llm/thread?limit=abc", {})
    assert code == 400
    code, _ = _truncate("", {"conversation_id": 1, "keep_count": -2})
    assert code == 400


def test_query_error_codes_fixed() -> None:
    """Query 400s carry fixed codes, never caller-controlled text."""

    class _Model:
        pass

    with pytest.raises(HTTPException) as exc:
        expression_clause(
            None, QueryCondition(field="x", operator="bogus", value=1)
        )
    assert exc.value.detail == "unsupported_operator"
    with pytest.raises(HTTPException) as exc:
        apply_expressions(
            None, _Model, [QueryCondition(field="nope", operator="eq")]
        )
    assert exc.value.detail == "unknown_field"
    with pytest.raises(HTTPException) as exc:
        apply_order_by(None, _Model, [OrderClause(field="nope")])
    assert exc.value.detail == "unknown_order_field"


def test_cors_wildcard_rejected(monkeypatch) -> None:
    """A '*' origin with credentials on refuses to build the app."""
    monkeypatch.setenv("AIRUNNER_API_KEY", "")
    with pytest.raises(ValueError):
        create_app(["*"])


def test_docs_hidden_from_non_loopback(monkeypatch) -> None:
    """Docs answer 404 to remote clients, 200 to loopback callers."""
    client = _client(monkeypatch)
    assert client.get("/docs").status_code == 404
    assert client.get("/openapi.json").status_code == 404
    monkeypatch.setattr(
        server_module, "is_loopback_request", lambda _c: True
    )
    assert client.get("/docs").status_code == 200


def test_socket_tenant_uses_shared_snapshot(monkeypatch) -> None:
    """Sockets enforce the startup snapshot, not a re-read env var."""
    monkeypatch.setenv("AIRUNNER_ALLOWED_TENANT_KEYS", "stale")
    state = SimpleNamespace(
        require_api_key=True, allowed_tenants={"snap-tenant"}
    )
    ws = SimpleNamespace(
        headers={"x-tenant-key": "snap-tenant"},
        app=SimpleNamespace(state=state),
        client=SimpleNamespace(host="127.0.0.1"),
    )
    baseline = set_tenant_key(None)
    try:
        token = scope_websocket_tenant(ws)
        assert token is not None
        assert get_tenant_key() == "snap-tenant"
        reset_tenant_key(token)
        assert get_tenant_key() is None
    finally:
        reset_tenant_key(baseline)


def test_llm_field_allowlist() -> None:
    """Dangerous LLM fields cannot be injected via legacy payloads."""
    request = build_llm_request(
        {
            "temperature": 99.0,
            "top_k": 5,
            "rag_files": ["/etc/passwd"],
            "images": ["x"],
            "dtype": "4bit",
            "model_service": "openrouter",
            "api_model": "evil",
            "force_tool": "shell",
            "prompt": "ignored",
            "action": "ignored",
        }
    )
    assert request.temperature == 0.7
    assert request.top_k == 5
    assert request.rag_files == []
    assert request.images == []
    assert request.dtype is None
    assert request.model_service is None
    assert request.api_model is None
    assert request.force_tool is None
