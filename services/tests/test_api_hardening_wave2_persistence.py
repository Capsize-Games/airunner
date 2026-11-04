"""Wave-2 API hardening: persistence data-plane guards.

Covers the removed ``delete_all`` op, empty-filter rejection and row
caps on bulk mutations, query pagination, and the mass-assignment
allowlist in ``normalized_values``.
"""

from __future__ import annotations

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from airunner_services.api.routes.persistence_contracts import (
    PersistenceRequest,
)
from airunner_services.api.routes.persistence_mutations import (
    _check_bulk_row_cap,
    _require_scoped_filters,
)
from airunner_services.api.routes.persistence_serialization import (
    normalized_values,
)
from airunner_services.api.server import create_app
from airunner_services.database import reset_engine, setup_database
from airunner_services.database.models.saved_prompt import SavedPrompt
from airunner_services.database.session import session_scope

_STATE = "/api/v1/state/settings/SavedPrompt"


@pytest.fixture()
def test_db(tmp_path, monkeypatch) -> str:
    """Point the ORM at a temp SQLite file."""
    db_url = f"sqlite:///{tmp_path / 'hardening.sqlite'}"
    monkeypatch.setenv("AIRUNNER_DATABASE_URL", db_url)
    monkeypatch.setenv("AIRUNNER_DISABLE_DB_SETUP_CACHE", "1")
    reset_engine()
    setup_database()
    return db_url


def _client(monkeypatch) -> TestClient:
    """Return a TestClient with auth disabled."""
    monkeypatch.setenv("AIRUNNER_API_KEY", "")
    monkeypatch.setenv("AIRUNNER_INSECURE_NO_AUTH", "1")
    return TestClient(create_app(enable_cors=False))


def _seed(count: int, prompt: str | None = None) -> None:
    """Insert count SavedPrompt rows."""
    with session_scope() as session:
        session.add_all(
            [
                SavedPrompt(prompt=prompt or f"p{i}")
                for i in range(count)
            ]
        )


def _op(operation: str, **extra) -> dict:
    """Build one persistence request payload."""
    payload = {
        "operation": operation,
        "values": {},
        "filters": {},
    }
    payload.update(extra)
    return payload


def test_delete_all_operation_removed(
    monkeypatch, test_db: str
) -> None:
    """The whole-table wipe op now answers 400, never wiping."""
    _seed(2)
    response = _client(monkeypatch).post(
        _STATE, json=_op("delete_all")
    )
    assert response.status_code == 400


def test_update_by_empty_filters_rejected(
    monkeypatch, test_db: str
) -> None:
    """Bulk update with no pk and no filters answers 400."""
    response = _client(monkeypatch).post(
        _STATE,
        json=_op("update_by", values={"prompt": "x"}),
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "bulk_mutation_requires_filters"


def test_delete_empty_filters_rejected(
    monkeypatch, test_db: str
) -> None:
    """Bulk delete with no pk and no filters answers 400."""
    _seed(1)
    response = _client(monkeypatch).post(
        _STATE, json=_op("delete")
    )
    assert response.status_code == 400


def test_scoped_bulk_guards_unit() -> None:
    """Guard helpers reject empty filters and over-cap counts."""
    with pytest.raises(HTTPException):
        _require_scoped_filters(PersistenceRequest(operation="x"))
    with pytest.raises(HTTPException):
        _check_bulk_row_cap(501)
    _check_bulk_row_cap(500)


def test_bulk_row_cap_enforced(
    monkeypatch, test_db: str
) -> None:
    """A 501-row match set is rejected before any write."""
    _seed(501, prompt="bulk")
    response = _client(monkeypatch).post(
        _STATE,
        json=_op(
            "update_by",
            values={"prompt": "capped"},
            filters={"prompt": "bulk"},
        ),
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "bulk_row_limit_exceeded"


def test_query_pagination_bounds(
    monkeypatch, test_db: str
) -> None:
    """Huge limits and negative offsets answer 400 with a fixed code."""
    client = _client(monkeypatch)
    for payload in (
        _op("query", limit=5000),
        _op("query", limit=0),
        _op("query", offset=-1),
    ):
        response = client.post(_STATE, json=payload)
        assert response.status_code == 400
        assert response.json()["detail"] == "invalid_pagination"


def test_query_pagination_applies(
    monkeypatch, test_db: str
) -> None:
    """Limit/offset page through the table instead of dumping it."""
    _seed(5)
    client = _client(monkeypatch)
    first = client.post(_STATE, json=_op("query", limit=2))
    assert first.status_code == 200
    assert len(first.json()["records"]) == 2
    rest = client.post(_STATE, json=_op("query", limit=10, offset=2))
    assert rest.status_code == 200
    assert len(rest.json()["records"]) == 3


def test_normalized_values_allowlist() -> None:
    """Unknown keys and the pk are dropped on update paths."""
    cleaned = normalized_values(
        SavedPrompt, {"id": 5, "prompt": "x", "nope": 1}
    )
    assert cleaned == {"prompt": "x"}
    kept = normalized_values(
        SavedPrompt, {"id": 5, "prompt": "x"}, allow_pk=True
    )
    assert kept == {"id": 5, "prompt": "x"}
