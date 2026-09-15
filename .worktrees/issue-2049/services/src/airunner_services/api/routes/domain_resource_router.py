"""Router factory for resource-oriented domain routes."""

from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter

from .domain_resource_contracts import DeleteRequest, MutationRequest, QueryRequest
from .domain_resource_store import (
    create_record,
    delete_record,
    delete_records,
    get_layer_record,
    get_singleton,
    query_records,
    update_record,
)


def build_domain_router(domain: str) -> APIRouter:
    """Build one router for a domain resource namespace."""
    router = APIRouter()

    @router.get("/resources/{resource}/singleton")
    async def get_singleton_route(
        resource: str,
        create_if_missing: bool = True,
    ) -> Dict[str, Any]:
        return get_singleton(
            domain,
            resource,
            create_if_missing=create_if_missing,
        )

    @router.put("/resources/{resource}/singleton")
    async def update_singleton(
        resource: str,
        body: MutationRequest,
    ) -> Dict[str, Any]:
        record = get_singleton(domain, resource, create_if_missing=True).get("record")
        if record is None:
            return create_record(domain, resource, body)
        return update_record(domain, resource, int(record["id"]), body)

    @router.get("/resources/{resource}/layers/{layer_id}")
    async def get_layer_resource(
        resource: str,
        layer_id: int,
        create_if_missing: bool = True,
    ) -> Dict[str, Any]:
        return get_layer_record(
            domain,
            resource,
            layer_id,
            create_if_missing=create_if_missing,
        )

    @router.put("/resources/{resource}/layers/{layer_id}")
    async def update_layer_resource(
        resource: str,
        layer_id: int,
        body: MutationRequest,
    ) -> Dict[str, Any]:
        record = get_layer_record(
            domain,
            resource,
            layer_id,
            create_if_missing=True,
        ).get("record")
        if record is not None:
            return update_record(domain, resource, int(record["id"]), body)
        values = dict(body.values)
        values["layer_id"] = layer_id
        return create_record(
            domain,
            resource,
            MutationRequest(values=values, eager_load=body.eager_load),
        )

    @router.post("/resources/{resource}/query")
    async def query_collection(
        resource: str,
        body: QueryRequest,
    ) -> Dict[str, Any]:
        return query_records(domain, resource, body, first=False)

    @router.post("/resources/{resource}/first")
    async def first_collection(
        resource: str,
        body: QueryRequest,
    ) -> Dict[str, Any]:
        return query_records(domain, resource, body, first=True)

    @router.get("/resources/{resource}/{record_id}")
    async def get_record(resource: str, record_id: int) -> Dict[str, Any]:
        return query_records(
            domain,
            resource,
            QueryRequest(filters={"id": record_id}, limit=1),
            first=True,
        )

    @router.post("/resources/{resource}")
    async def create_record_route(
        resource: str,
        body: MutationRequest,
    ) -> Dict[str, Any]:
        return create_record(domain, resource, body)

    @router.put("/resources/{resource}/{record_id}")
    async def update_record_route(
        resource: str,
        record_id: int,
        body: MutationRequest,
    ) -> Dict[str, Any]:
        return update_record(domain, resource, record_id, body)

    @router.delete("/resources/{resource}/{record_id}")
    async def delete_record_route(
        resource: str,
        record_id: int,
    ) -> Dict[str, Any]:
        return delete_record(domain, resource, record_id)

    @router.post("/resources/{resource}/delete")
    async def delete_records_route(
        resource: str,
        body: DeleteRequest,
    ) -> Dict[str, Any]:
        return delete_records(domain, resource, body)

    return router