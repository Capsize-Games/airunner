"""Contracts for resource-oriented domain routes."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class OrderClause(BaseModel):
    """Ordering clause for one resource query."""

    field: str
    direction: str = "asc"


class QueryRequest(BaseModel):
    """Request payload for collection queries."""

    filters: Dict[str, Any] = Field(default_factory=dict)
    order_by: List[OrderClause] = Field(default_factory=list)
    eager_load: List[str] = Field(default_factory=list)
    limit: Optional[int] = None


class MutationRequest(BaseModel):
    """Request payload for create and update operations."""

    values: Dict[str, Any] = Field(default_factory=dict)
    eager_load: List[str] = Field(default_factory=list)


class DeleteRequest(BaseModel):
    """Request payload for bulk delete operations."""

    filters: Dict[str, Any] = Field(default_factory=dict)


__all__ = [
    "DeleteRequest",
    "MutationRequest",
    "OrderClause",
    "QueryRequest",
]