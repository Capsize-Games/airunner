"""Mutation helpers for daemon-backed persistence routes."""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException

from airunner_services.database.session import session_scope

from .persistence_contracts import PersistenceRequest, PersistenceResponse
from .persistence_query import apply_eager_load
from .persistence_serialization import normalized_values, serialize_record

_MAX_BULK_ROWS = 500


def _require_scoped_filters(body: PersistenceRequest) -> None:
    """Reject filter-path mutations that would touch every row."""
    if body.pk is None and not body.filters:
        raise HTTPException(
            status_code=400, detail="bulk_mutation_requires_filters"
        )


def _require_nonempty_filters(body: PersistenceRequest) -> None:
    """Reject bulk updates scoped by an empty filter dict.

    ``update_by`` never consults ``pk``, so a pk cannot scope it: only
    a non-empty filter set may select rows.
    """
    if not body.filters:
        raise HTTPException(
            status_code=400, detail="bulk_mutation_requires_filters"
        )


def _check_bulk_row_cap(count: int) -> None:
    """Reject bulk mutations whose match set exceeds the row cap."""
    if count > _MAX_BULK_ROWS:
        raise HTTPException(
            status_code=400, detail="bulk_row_limit_exceeded"
        )


def _enforce_tool_safety(record: Any) -> None:
    """Fail closed for LLMTool records: never trust a caller-supplied flag.

    ``safety_validated`` may only be True after ``validate_code_safety``
    actually passes; otherwise it is persisted as False (GitHub issue #2032).
    """
    from airunner_services.database.models.llm_tool import LLMTool

    if not isinstance(record, LLMTool):
        return
    is_safe, _message = record.validate_code_safety()
    record.safety_validated = is_safe


def _enforce_tool_code_values(model_cls: type[Any], values: dict[str, Any]) -> None:
    """Re-run tool validation when a bulk update touches tool code."""
    from airunner_services.database.models.llm_tool import LLMTool

    if model_cls is not LLMTool or "code" not in values:
        return
    is_safe, _message = LLMTool(code=values["code"]).validate_code_safety()
    values["safety_validated"] = is_safe


def create_record(
    model_cls: type[Any],
    body: PersistenceRequest,
) -> PersistenceResponse:
    """Create one service-owned ORM record."""
    with session_scope() as session:
        result = model_cls(
            **normalized_values(model_cls, body.values, allow_pk=True)
        )
        _enforce_tool_safety(result)
        session.add(result)
        session.flush()
        session.refresh(result)
        return PersistenceResponse(record=serialize_record(result))


def get_or_create_record(
    model_cls: type[Any],
    body: PersistenceRequest,
) -> PersistenceResponse:
    """Get or create one ORM record using service ownership."""
    with session_scope() as session:
        query = apply_eager_load(session.query(model_cls), model_cls, body.eager_load)
        result = query.filter_by(**body.filters).first() if body.filters else query.first()
        if result is not None:
            return PersistenceResponse(
                record=serialize_record(result, eager_load=body.eager_load),
                created=False,
            )
        create_values = normalized_values(
            model_cls, body.defaults, allow_pk=True
        )
        create_values.update(body.filters)
        result = model_cls(**create_values)
        session.add(result)
        session.flush()
        session.refresh(result)
        return PersistenceResponse(
            record=serialize_record(result, eager_load=body.eager_load),
            created=True,
        )


def merge_record(
    model_cls: type[Any],
    body: PersistenceRequest,
) -> PersistenceResponse:
    """Merge one detached ORM record into the service session."""
    with session_scope() as session:
        result = session.merge(
            model_cls(
                **normalized_values(
                    model_cls, body.values, allow_pk=True
                )
            )
        )
        _enforce_tool_safety(result)
        session.flush()
        session.refresh(result)
        return PersistenceResponse(record=serialize_record(result))


def update_record(
    model_cls: type[Any],
    body: PersistenceRequest,
) -> PersistenceResponse:
    """Update one ORM record by id or first row."""
    with session_scope() as session:
        query = session.query(model_cls)
        result = query.filter(model_cls.id == body.pk).first() if body.pk is not None else query.first()
        if result is None:
            return PersistenceResponse(success=False)
        for key, value in normalized_values(model_cls, body.values).items():
            setattr(result, key, value)
        _enforce_tool_safety(result)
        session.add(result)
        session.flush()
        return PersistenceResponse(success=True)


def update_by(
    model_cls: type[Any],
    body: PersistenceRequest,
) -> PersistenceResponse:
    """Bulk-update records matching one filter dict."""
    _require_nonempty_filters(body)
    with session_scope() as session:
        values = normalized_values(model_cls, body.values)
        _enforce_tool_code_values(model_cls, values)
        query = session.query(model_cls).filter_by(**body.filters)
        _check_bulk_row_cap(query.count())
        count = query.update(values, synchronize_session=False)
        return PersistenceResponse(success=bool(count), count=int(count or 0))


def delete_record(
    model_cls: type[Any],
    body: PersistenceRequest,
) -> PersistenceResponse:
    """Delete one record by id or one filter dict."""
    with session_scope() as session:
        query = session.query(model_cls)
        if body.pk is not None:
            result = query.filter(model_cls.id == body.pk).first()
            if result is None:
                return PersistenceResponse(success=False, count=0)
            session.delete(result)
            return PersistenceResponse(success=True, count=1)
        _require_scoped_filters(body)
        filtered = query.filter_by(**body.filters)
        _check_bulk_row_cap(filtered.count())
        count = filtered.delete()
        return PersistenceResponse(success=bool(count), count=int(count or 0))