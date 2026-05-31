"""Domain-scoped state routes for daemon-backed GUI persistence."""

from __future__ import annotations

from typing import Callable

from fastapi import APIRouter, HTTPException
from .persistence_contracts import (
    OrderClause,
    PersistenceRequest,
    PersistenceResponse,
    QueryCondition,
)
from .persistence_mutations import (
    create_record,
    delete_all,
    delete_record,
    get_or_create_record,
    merge_record,
    update_by,
    update_record,
)
from .persistence_query import query_records
from .persistence_registry import model_class


router = APIRouter()

OperationHandler = Callable[[type, PersistenceRequest], PersistenceResponse]
OPERATION_HANDLERS: dict[str, OperationHandler] = {
    "query": query_records,
    "create": create_record,
    "get_or_create": get_or_create_record,
    "merge": merge_record,
    "update": update_record,
    "update_by": update_by,
    "delete": delete_record,
}


@router.post("/{domain}/{model_name}", response_model=PersistenceResponse)
def execute_state_operation(
    domain: str,
    model_name: str,
    body: PersistenceRequest,
) -> PersistenceResponse:
    """Execute one state operation on one service-owned domain model."""
    model_cls = model_class(domain, model_name)
    operation = body.operation.lower().strip()
    if operation == "delete_all":
        return delete_all(model_cls)
    handler = OPERATION_HANDLERS.get(operation)
    if handler is not None:
        return handler(model_cls, body)
    raise HTTPException(status_code=400, detail="Unsupported operation")


__all__ = [
    "OrderClause",
    "PersistenceRequest",
    "PersistenceResponse",
    "QueryCondition",
    "execute_state_operation",
    "router",
]