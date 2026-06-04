"""Mutation helpers for daemon-backed persistence routes."""

from __future__ import annotations

from typing import Any

from airunner_services.database.session import session_scope

from .persistence_contracts import PersistenceRequest, PersistenceResponse
from .persistence_query import apply_eager_load
from .persistence_serialization import normalized_values, serialize_record


def create_record(
    model_cls: type[Any],
    body: PersistenceRequest,
) -> PersistenceResponse:
    """Create one service-owned ORM record."""
    with session_scope() as session:
        result = model_cls(**normalized_values(model_cls, body.values))
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
        create_values = normalized_values(model_cls, body.defaults)
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
        result = session.merge(model_cls(**normalized_values(model_cls, body.values)))
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
        session.add(result)
        session.flush()
        return PersistenceResponse(success=True)


def update_by(
    model_cls: type[Any],
    body: PersistenceRequest,
) -> PersistenceResponse:
    """Bulk-update records matching one filter dict."""
    with session_scope() as session:
        values = normalized_values(model_cls, body.values)
        count = (
            session.query(model_cls)
            .filter_by(**body.filters)
            .update(values, synchronize_session=False)
        )
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
        count = query.filter_by(**body.filters).delete()
        return PersistenceResponse(success=bool(count), count=int(count or 0))


def delete_all(model_cls: type[Any]) -> PersistenceResponse:
    """Delete all rows for one model."""
    with session_scope() as session:
        count = session.query(model_cls).delete()
        return PersistenceResponse(success=True, count=int(count or 0))