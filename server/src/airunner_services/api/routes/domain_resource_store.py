"""Storage helpers for resource-oriented domain routes."""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException

from airunner_services.database.session import session_scope

from .domain_resource_contracts import DeleteRequest, MutationRequest, QueryRequest
from .domain_resource_registry import assert_layer_resource, assert_singleton
from .persistence_query import apply_eager_load, apply_order_by
from .persistence_registry import model_class
from .persistence_serialization import normalized_values, serialize_record


def query_options(query, model_cls: type[Any], body: QueryRequest):
    """Apply shared query options for one domain resource request."""
    query = apply_eager_load(query, model_cls, body.eager_load)
    if body.filters:
        query = query.filter_by(**body.filters)
    return apply_order_by(query, model_cls, body.order_by)


def query_records(
    domain: str,
    resource: str,
    body: QueryRequest,
    *,
    first: bool = False,
) -> dict[str, Any]:
    """Execute one collection query for one registered resource."""
    resource_model = model_class(domain, resource)
    with session_scope() as session:
        query = query_options(session.query(resource_model), resource_model, body)
        if first:
            record = query.first()
            payload = None
            if record is not None:
                payload = serialize_record(record, eager_load=body.eager_load)
            return {"record": payload}
        if body.limit is not None and body.limit >= 0:
            query = query.limit(body.limit)
        records = query.all()
        return {
            "records": [
                serialize_record(item, eager_load=body.eager_load)
                for item in records
            ]
        }


def create_record(
    domain: str,
    resource: str,
    body: MutationRequest,
) -> dict[str, Any]:
    """Create one record for one registered resource."""
    resource_model = model_class(domain, resource)
    with session_scope() as session:
        record = resource_model(**normalized_values(resource_model, body.values))
        session.add(record)
        session.flush()
        session.refresh(record)
        return {"record": serialize_record(record, eager_load=body.eager_load)}


def update_record(
    domain: str,
    resource: str,
    record_id: int,
    body: MutationRequest,
) -> dict[str, Any]:
    """Update one record for one registered resource."""
    resource_model = model_class(domain, resource)
    with session_scope() as session:
        record = session.query(resource_model).filter_by(id=record_id).first()
        if record is None:
            raise HTTPException(status_code=404, detail="Record not found")
        for key, value in normalized_values(resource_model, body.values).items():
            setattr(record, key, value)
        session.flush()
        session.refresh(record)
        return {"record": serialize_record(record, eager_load=body.eager_load)}


def delete_record(domain: str, resource: str, record_id: int) -> dict[str, Any]:
    """Delete one record by primary key."""
    resource_model = model_class(domain, resource)
    with session_scope() as session:
        record = session.query(resource_model).filter_by(id=record_id).first()
        if record is None:
            raise HTTPException(status_code=404, detail="Record not found")
        session.delete(record)
        session.flush()
    return {"deleted": True, "count": 1}


def delete_records(
    domain: str,
    resource: str,
    body: DeleteRequest,
) -> dict[str, Any]:
    """Delete many records that match one filter map."""
    resource_model = model_class(domain, resource)
    with session_scope() as session:
        query = session.query(resource_model)
        if body.filters:
            query = query.filter_by(**body.filters)
        records = query.all()
        count = len(records)
        for record in records:
            session.delete(record)
        session.flush()
    return {"deleted": True, "count": count}


def get_singleton(
    domain: str,
    resource: str,
    *,
    create_if_missing: bool,
) -> dict[str, Any]:
    """Return one singleton resource payload, creating when requested."""
    assert_singleton(domain, resource)
    response = query_records(domain, resource, QueryRequest(limit=1), first=True)
    if response.get("record") is not None or not create_if_missing:
        return response
    return create_record(domain, resource, MutationRequest())


def get_layer_record(
    domain: str,
    resource: str,
    layer_id: int,
    *,
    create_if_missing: bool,
) -> dict[str, Any]:
    """Return one layer-scoped record payload for a resource."""
    assert_layer_resource(domain, resource)
    response = query_records(
        domain,
        resource,
        QueryRequest(filters={"layer_id": layer_id}, limit=1),
        first=True,
    )
    if response.get("record") is not None or not create_if_missing:
        return response
    return create_record(
        domain,
        resource,
        MutationRequest(values={"layer_id": layer_id}),
    )