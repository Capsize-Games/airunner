"""Contracts for daemon-backed persistence routes."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class QueryCondition(BaseModel):
    """Serialized query condition for one model field."""

    field: str
    operator: str
    value: Any = None


class OrderClause(BaseModel):
    """Serialized ordering clause."""

    field: str
    direction: str = "asc"


class PersistenceRequest(BaseModel):
    """Generic persistence operation request payload."""

    operation: str
    pk: Optional[int] = None
    first: bool = False
    values: Dict[str, Any] = Field(default_factory=dict)
    defaults: Dict[str, Any] = Field(default_factory=dict)
    filters: Dict[str, Any] = Field(default_factory=dict)
    expressions: List[QueryCondition] = Field(default_factory=list)
    order_by: List[OrderClause] = Field(default_factory=list)
    eager_load: List[str] = Field(default_factory=list)


class PersistenceResponse(BaseModel):
    """Generic persistence response payload."""

    record: Optional[Dict[str, Any]] = None
    records: List[Dict[str, Any]] = Field(default_factory=list)
    success: Optional[bool] = None
    count: Optional[int] = None
    created: Optional[bool] = None


__all__ = [
    "OrderClause",
    "PersistenceRequest",
    "PersistenceResponse",
    "QueryCondition",
]