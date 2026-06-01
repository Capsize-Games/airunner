"""Query helpers for daemon-backed persistence routes."""

from __future__ import annotations

from typing import Any, Callable

from fastapi import HTTPException
from sqlalchemy.orm import Query, subqueryload

from airunner_services.database.session import session_scope

from .persistence_contracts import (
    OrderClause,
    PersistenceRequest,
    PersistenceResponse,
    QueryCondition,
)
from .persistence_serialization import serialize_record

ExpressionBuilder = Callable[[Any, Any], Any]
EXPRESSION_BUILDERS: dict[str, ExpressionBuilder] = {
    "eq": lambda column, value: column == value,
    "ne": lambda column, value: column != value,
    "ge": lambda column, value: column >= value,
    "gt": lambda column, value: column > value,
    "le": lambda column, value: column <= value,
    "lt": lambda column, value: column < value,
    "in": lambda column, value: column.in_(value or []),
    "is": lambda column, value: column.is_(value),
    "is_": lambda column, value: column.is_(value),
    "is_not": lambda column, value: column.is_not(value),
    "isnot": lambda column, value: column.is_not(value),
}


def apply_eager_load(
    query: Query,
    model_cls: type[Any],
    eager_load: list[str],
) -> Query:
    """Apply requested relationship eager loading to one query."""
    for relationship_name in eager_load:
        rel_attr = getattr(model_cls, relationship_name, None)
        if rel_attr is None:
            continue
        query = query.options(subqueryload(rel_attr))
    return query


def expression_clause(column: Any, expression: QueryCondition) -> Any:
    """Return one SQLAlchemy clause from one serialized query condition."""
    builder = EXPRESSION_BUILDERS.get(expression.operator.lower())
    if builder is None:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported operator: {expression.operator}",
        )
    return builder(column, expression.value)


def apply_expressions(
    query: Query,
    model_cls: type[Any],
    expressions: list[QueryCondition],
) -> Query:
    """Apply serialized filter expressions to one query."""
    for expression in expressions:
        column = getattr(model_cls, expression.field, None)
        if column is None:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown field: {expression.field}",
            )
        query = query.filter(expression_clause(column, expression))
    return query


def apply_order_by(
    query: Query,
    model_cls: type[Any],
    clauses: list[OrderClause],
) -> Query:
    """Apply serialized ordering to one query."""
    for clause in clauses:
        column = getattr(model_cls, clause.field, None)
        if column is None:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown order field: {clause.field}",
            )
        direction = clause.direction.lower()
        query = query.order_by(column.desc() if direction == "desc" else column.asc())
    return query


def query_records(
    model_cls: type[Any],
    body: PersistenceRequest,
) -> PersistenceResponse:
    """Execute one serialized query against one service model."""
    with session_scope() as session:
        query = session.query(model_cls)
        query = apply_eager_load(query, model_cls, body.eager_load)
        if body.pk is not None:
            query = query.filter(model_cls.id == body.pk)
        if body.filters:
            query = query.filter_by(**body.filters)
        query = apply_expressions(query, model_cls, body.expressions)
        query = apply_order_by(query, model_cls, body.order_by)
        if body.first or body.pk is not None:
            result = query.first()
            if result is None:
                return PersistenceResponse(record=None)
            return PersistenceResponse(
                record=serialize_record(result, eager_load=body.eager_load)
            )
        results = query.all()
        return PersistenceResponse(
            records=[
                serialize_record(item, eager_load=body.eager_load)
                for item in results
            ]
        )