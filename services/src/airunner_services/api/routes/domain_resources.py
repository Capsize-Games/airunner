"""Resource-oriented domain routes for GUI data clients."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import DateTime
from sqlalchemy.inspection import inspect as sqlalchemy_inspect
from sqlalchemy.orm import Query, subqueryload

from airunner_services.database import models as database_models
from airunner_services.database.session import session_scope


_DOMAIN_MODELS = {
    "settings": {
        "AIRunnerSettings",
        "ActiveGridSettings",
        "ApplicationSettings",
        "BrushSettings",
        "CanvasLayer",
        "Chatbot",
        "ControlnetSettings",
        "DrawingPadSettings",
        "EspeakSettings",
        "FontSetting",
        "GeneratorSettings",
        "GridSettings",
        "ImageToImageSettings",
        "LanguageSettings",
        "LLMGeneratorSettings",
        "MemorySettings",
        "MetadataSettings",
        "OpenVoiceSettings",
        "OutpaintSettings",
        "PathSettings",
        "PromptTemplate",
        "RAGSettings",
        "SavedPrompt",
        "ShortcutKeys",
        "SoundSettings",
        "STTSettings",
        "TargetDirectories",
        "TargetFiles",
        "User",
        "VoiceSettings",
        "WhisperSettings",
    },
    "catalog": {
        "AIModels",
        "ControlnetModel",
        "Embedding",
        "FineTunedModel",
        "ImageFilter",
        "ImageFilterValue",
        "Lora",
        "PipelineModel",
        "Schedulers",
    },
    "library": {"Document", "ZimFile"},
    "workspace": {
        "AgentConfig",
        "DecisionMemory",
        "LLMTool",
        "ProgressEntry",
        "ProjectFeature",
        "ProjectState",
        "SessionState",
    },
}

_SINGLETON_RESOURCES = {
    "settings": {
        "AIRunnerSettings",
        "ActiveGridSettings",
        "ApplicationSettings",
        "BrushSettings",
        "GeneratorSettings",
        "GridSettings",
        "LanguageSettings",
        "LLMGeneratorSettings",
        "MemorySettings",
        "PathSettings",
        "RAGSettings",
        "SoundSettings",
        "STTSettings",
        "WhisperSettings",
    },
}

_LAYER_RESOURCES = {
    "settings": {
        "ControlnetSettings",
        "DrawingPadSettings",
        "ImageToImageSettings",
        "MetadataSettings",
        "OutpaintSettings",
    },
}

_MODEL_BY_NAME = {
    model_name: getattr(database_models, model_name)
    for model_names in _DOMAIN_MODELS.values()
    for model_name in model_names
}


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


def _model_class(domain: str, resource: str):
    """Return the service-owned ORM class for one resource name."""
    if resource not in _DOMAIN_MODELS.get(domain, set()):
        raise HTTPException(status_code=404, detail="Resource not found")
    model_cls = _MODEL_BY_NAME.get(resource)
    if model_cls is None:
        raise HTTPException(status_code=404, detail="Resource not found")
    return model_cls


def _assert_singleton(domain: str, resource: str) -> None:
    """Validate that one resource is registered as a singleton."""
    if resource not in _SINGLETON_RESOURCES.get(domain, set()):
        raise HTTPException(status_code=404, detail="Singleton not found")


def _assert_layer_resource(domain: str, resource: str) -> None:
    """Validate that one resource is registered as layer-scoped."""
    if resource not in _LAYER_RESOURCES.get(domain, set()):
        raise HTTPException(status_code=404, detail="Layer resource not found")


def _column_payload(record: Any) -> Dict[str, Any]:
    """Return mapped column values for one ORM record."""
    mapper = sqlalchemy_inspect(record).mapper
    return {
        column.key: getattr(record, column.key)
        for column in mapper.column_attrs
    }


def _serialize_record(
    record: Any,
    *,
    eager_load: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Serialize one ORM record into a JSON-safe payload."""
    payload = _column_payload(record)
    mapper = sqlalchemy_inspect(type(record)).mapper
    for relationship_name in eager_load or []:
        if relationship_name not in mapper.relationships:
            continue
        relationship_value = getattr(record, relationship_name)
        relationship_prop = mapper.relationships[relationship_name]
        if relationship_value is None:
            payload[relationship_name] = None
            continue
        if relationship_prop.uselist:
            payload[relationship_name] = [
                _column_payload(item) for item in relationship_value
            ]
            continue
        payload[relationship_name] = _column_payload(relationship_value)
    return payload


def _normalized_values(
    model_cls: type[Any],
    values: Dict[str, Any],
) -> Dict[str, Any]:
    """Normalize serialized values into ORM-ready Python values."""
    mapper = sqlalchemy_inspect(model_cls).mapper
    column_types = {
        column.key: column.columns[0].type
        for column in mapper.column_attrs
    }
    normalized: Dict[str, Any] = {}
    for key, value in values.items():
        column_type = column_types.get(key)
        if isinstance(value, str) and isinstance(column_type, DateTime):
            try:
                normalized[key] = datetime.fromisoformat(value)
                continue
            except ValueError:
                pass
        normalized[key] = value
    return normalized


def _apply_query_options(
    query: Query,
    model_cls: type[Any],
    body: QueryRequest,
) -> Query:
    """Apply eager loading, filters, and ordering to one query."""
    for relationship_name in body.eager_load:
        rel_attr = getattr(model_cls, relationship_name, None)
        if rel_attr is not None:
            query = query.options(subqueryload(rel_attr))
    if body.filters:
        query = query.filter_by(**body.filters)
    for clause in body.order_by:
        column = getattr(model_cls, clause.field, None)
        if column is None:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown order field: {clause.field}",
            )
        if clause.direction.lower() == "desc":
            query = query.order_by(column.desc())
            continue
        query = query.order_by(column.asc())
    return query


def _query_records(
    domain: str,
    resource: str,
    body: QueryRequest,
    *,
    first: bool = False,
) -> Dict[str, Any]:
    """Execute one collection query for one registered resource."""
    model_cls = _model_class(domain, resource)
    with session_scope() as session:
        query = _apply_query_options(session.query(model_cls), model_cls, body)
        if first:
            record = query.first()
            return {
                "record": None
                if record is None
                else _serialize_record(record, eager_load=body.eager_load)
            }
        if body.limit is not None and body.limit >= 0:
            query = query.limit(body.limit)
        records = query.all()
        return {
            "records": [
                _serialize_record(item, eager_load=body.eager_load)
                for item in records
            ]
        }


def _create_record(
    domain: str,
    resource: str,
    body: MutationRequest,
) -> Dict[str, Any]:
    """Create one record for one registered resource."""
    model_cls = _model_class(domain, resource)
    with session_scope() as session:
        record = model_cls(**_normalized_values(model_cls, body.values))
        session.add(record)
        session.flush()
        session.refresh(record)
        return {
            "record": _serialize_record(record, eager_load=body.eager_load)
        }


def _update_record(
    domain: str,
    resource: str,
    record_id: int,
    body: MutationRequest,
) -> Dict[str, Any]:
    """Update one record for one registered resource."""
    model_cls = _model_class(domain, resource)
    with session_scope() as session:
        record = session.query(model_cls).filter_by(id=record_id).first()
        if record is None:
            raise HTTPException(status_code=404, detail="Record not found")
        for key, value in _normalized_values(model_cls, body.values).items():
            setattr(record, key, value)
        session.flush()
        session.refresh(record)
        return {
            "record": _serialize_record(record, eager_load=body.eager_load)
        }


def _delete_record(domain: str, resource: str, record_id: int) -> Dict[str, Any]:
    """Delete one record by primary key."""
    model_cls = _model_class(domain, resource)
    with session_scope() as session:
        record = session.query(model_cls).filter_by(id=record_id).first()
        if record is None:
            raise HTTPException(status_code=404, detail="Record not found")
        session.delete(record)
        session.flush()
    return {"deleted": True, "count": 1}


def _delete_records(
    domain: str,
    resource: str,
    body: DeleteRequest,
) -> Dict[str, Any]:
    """Delete many records that match one filter map."""
    model_cls = _model_class(domain, resource)
    with session_scope() as session:
        query = session.query(model_cls)
        if body.filters:
            query = query.filter_by(**body.filters)
        records = query.all()
        count = len(records)
        for record in records:
            session.delete(record)
        session.flush()
    return {"deleted": True, "count": count}


def _get_singleton(
    domain: str,
    resource: str,
    *,
    create_if_missing: bool,
) -> Dict[str, Any]:
    """Return one singleton resource payload, creating when requested."""
    _assert_singleton(domain, resource)
    response = _query_records(domain, resource, QueryRequest(limit=1), first=True)
    if response.get("record") is not None or not create_if_missing:
        return response
    return _create_record(domain, resource, MutationRequest())


def _get_layer_record(
    domain: str,
    resource: str,
    layer_id: int,
    *,
    create_if_missing: bool,
) -> Dict[str, Any]:
    """Return one layer-scoped record payload for a resource."""
    _assert_layer_resource(domain, resource)
    response = _query_records(
        domain,
        resource,
        QueryRequest(filters={"layer_id": layer_id}, limit=1),
        first=True,
    )
    if response.get("record") is not None or not create_if_missing:
        return response
    return _create_record(
        domain,
        resource,
        MutationRequest(values={"layer_id": layer_id}),
    )


def _build_domain_router(domain: str) -> APIRouter:
    """Build one router for a domain resource namespace."""
    router = APIRouter()

    @router.get("/resources/{resource}/singleton")
    async def get_singleton(
        resource: str,
        create_if_missing: bool = True,
    ) -> Dict[str, Any]:
        return _get_singleton(domain, resource, create_if_missing=create_if_missing)

    @router.put("/resources/{resource}/singleton")
    async def update_singleton(
        resource: str,
        body: MutationRequest,
    ) -> Dict[str, Any]:
        record = _get_singleton(domain, resource, create_if_missing=True).get(
            "record"
        )
        if record is None:
            return _create_record(domain, resource, body)
        return _update_record(domain, resource, int(record["id"]), body)

    @router.get("/resources/{resource}/layers/{layer_id}")
    async def get_layer_resource(
        resource: str,
        layer_id: int,
        create_if_missing: bool = True,
    ) -> Dict[str, Any]:
        return _get_layer_record(
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
        record = _get_layer_record(
            domain,
            resource,
            layer_id,
            create_if_missing=True,
        ).get("record")
        if record is None:
            values = dict(body.values)
            values["layer_id"] = layer_id
            return _create_record(
                domain,
                resource,
                MutationRequest(values=values, eager_load=body.eager_load),
            )
        return _update_record(domain, resource, int(record["id"]), body)

    @router.post("/resources/{resource}/query")
    async def query_collection(
        resource: str,
        body: QueryRequest,
    ) -> Dict[str, Any]:
        return _query_records(domain, resource, body, first=False)

    @router.post("/resources/{resource}/first")
    async def first_collection(
        resource: str,
        body: QueryRequest,
    ) -> Dict[str, Any]:
        return _query_records(domain, resource, body, first=True)

    @router.get("/resources/{resource}/{record_id}")
    async def get_record(resource: str, record_id: int) -> Dict[str, Any]:
        return _query_records(
            domain,
            resource,
            QueryRequest(filters={"id": record_id}, limit=1),
            first=True,
        )

    @router.post("/resources/{resource}")
    async def create_record(
        resource: str,
        body: MutationRequest,
    ) -> Dict[str, Any]:
        return _create_record(domain, resource, body)

    @router.put("/resources/{resource}/{record_id}")
    async def update_record(
        resource: str,
        record_id: int,
        body: MutationRequest,
    ) -> Dict[str, Any]:
        return _update_record(domain, resource, record_id, body)

    @router.delete("/resources/{resource}/{record_id}")
    async def delete_record(resource: str, record_id: int) -> Dict[str, Any]:
        return _delete_record(domain, resource, record_id)

    @router.post("/resources/{resource}/delete")
    async def delete_records(
        resource: str,
        body: DeleteRequest,
    ) -> Dict[str, Any]:
        return _delete_records(domain, resource, body)

    return router


settings_router = _build_domain_router("settings")
catalog_router = _build_domain_router("catalog")
library_router = _build_domain_router("library")
workspace_router = _build_domain_router("workspace")


__all__ = [
    "catalog_router",
    "library_router",
    "settings_router",
    "workspace_router",
]