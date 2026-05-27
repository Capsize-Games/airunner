"""Domain-scoped state routes for daemon-backed GUI persistence."""

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


router = APIRouter()
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
_MODEL_BY_NAME = {
    model_name: getattr(database_models, model_name)
    for model_names in _DOMAIN_MODELS.values()
    for model_name in model_names
}


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


def _model_class(domain: str, model_name: str):
    """Return one registered service model class for a state domain."""
    if model_name not in _DOMAIN_MODELS.get(domain, set()):
        raise HTTPException(status_code=404, detail="Model not found")
    model_cls = _MODEL_BY_NAME.get(model_name)
    if model_cls is None:
        raise HTTPException(status_code=404, detail="Model not found")
    return model_cls


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
    """Serialize one ORM record for GUI model hydration."""
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
    """Convert serialized payload values into ORM-ready Python values."""
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


def _apply_eager_load(
    query: Query,
    model_cls: type[Any],
    eager_load: List[str],
) -> Query:
    """Apply requested relationship eager loading to one query."""
    for relationship_name in eager_load:
        rel_attr = getattr(model_cls, relationship_name, None)
        if rel_attr is None:
            continue
        query = query.options(subqueryload(rel_attr))
    return query


def _apply_expressions(
    query: Query,
    model_cls: type[Any],
    expressions: List[QueryCondition],
) -> Query:
    """Apply serialized filter expressions to one query."""
    for expression in expressions:
        column = getattr(model_cls, expression.field, None)
        if column is None:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown field: {expression.field}",
            )
        operator = expression.operator.lower()
        value = expression.value
        if operator == "eq":
            query = query.filter(column == value)
        elif operator == "ne":
            query = query.filter(column != value)
        elif operator == "ge":
            query = query.filter(column >= value)
        elif operator == "gt":
            query = query.filter(column > value)
        elif operator == "le":
            query = query.filter(column <= value)
        elif operator == "lt":
            query = query.filter(column < value)
        elif operator == "in":
            query = query.filter(column.in_(value or []))
        elif operator in ("is", "is_"):
            query = query.filter(column.is_(value))
        elif operator in ("is_not", "isnot"):
            query = query.filter(column.is_not(value))
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported operator: {expression.operator}",
            )
    return query


def _apply_order_by(
    query: Query,
    model_cls: type[Any],
    clauses: List[OrderClause],
) -> Query:
    """Apply serialized ordering to one query."""
    for clause in clauses:
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
    model_cls: type[Any],
    body: PersistenceRequest,
) -> PersistenceResponse:
    """Execute one serialized query against one service model."""
    with session_scope() as session:
        query = session.query(model_cls)
        query = _apply_eager_load(query, model_cls, body.eager_load)
        if body.pk is not None:
            query = query.filter(model_cls.id == body.pk)
        if body.filters:
            query = query.filter_by(**body.filters)
        query = _apply_expressions(query, model_cls, body.expressions)
        query = _apply_order_by(query, model_cls, body.order_by)

        if body.first or body.pk is not None:
            result = query.first()
            if result is None:
                return PersistenceResponse(record=None)
            return PersistenceResponse(
                record=_serialize_record(result, eager_load=body.eager_load)
            )

        results = query.all()
        return PersistenceResponse(
            records=[
                _serialize_record(item, eager_load=body.eager_load)
                for item in results
            ]
        )


def _create_record(
    model_cls: type[Any],
    body: PersistenceRequest,
) -> PersistenceResponse:
    """Create one service-owned ORM record."""
    with session_scope() as session:
        result = model_cls(**_normalized_values(model_cls, body.values))
        session.add(result)
        session.flush()
        session.refresh(result)
        return PersistenceResponse(record=_serialize_record(result))


def _get_or_create_record(
    model_cls: type[Any],
    body: PersistenceRequest,
) -> PersistenceResponse:
    """Get or create one ORM record using service ownership."""
    with session_scope() as session:
        query = session.query(model_cls)
        query = _apply_eager_load(query, model_cls, body.eager_load)
        if body.filters:
            result = query.filter_by(**body.filters).first()
        else:
            result = query.first()
        if result is not None:
            return PersistenceResponse(
                record=_serialize_record(result, eager_load=body.eager_load),
                created=False,
            )

        create_values = _normalized_values(model_cls, body.defaults)
        create_values.update(body.filters)
        result = model_cls(**create_values)
        session.add(result)
        session.flush()
        session.refresh(result)
        return PersistenceResponse(
            record=_serialize_record(result, eager_load=body.eager_load),
            created=True,
        )


def _merge_record(
    model_cls: type[Any],
    body: PersistenceRequest,
) -> PersistenceResponse:
    """Merge one detached ORM record into the service session."""
    with session_scope() as session:
        result = session.merge(
            model_cls(**_normalized_values(model_cls, body.values))
        )
        session.flush()
        session.refresh(result)
        return PersistenceResponse(record=_serialize_record(result))


def _update_record(
    model_cls: type[Any],
    body: PersistenceRequest,
) -> PersistenceResponse:
    """Update one ORM record by id or first row."""
    with session_scope() as session:
        query = session.query(model_cls)
        if body.pk is not None:
            result = query.filter(model_cls.id == body.pk).first()
        else:
            result = query.first()
        if result is None:
            return PersistenceResponse(success=False)

        for key, value in _normalized_values(model_cls, body.values).items():
            setattr(result, key, value)
        session.add(result)
        session.flush()
        return PersistenceResponse(success=True)


def _update_by(
    model_cls: type[Any],
    body: PersistenceRequest,
) -> PersistenceResponse:
    """Bulk-update records matching one filter dict."""
    with session_scope() as session:
        values = _normalized_values(model_cls, body.values)
        count = (
            session.query(model_cls)
            .filter_by(**body.filters)
            .update(values, synchronize_session=False)
        )
        return PersistenceResponse(success=bool(count), count=int(count or 0))


def _delete_record(
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


def _delete_all(model_cls: type[Any]) -> PersistenceResponse:
    """Delete all rows for one model."""
    with session_scope() as session:
        count = session.query(model_cls).delete()
        return PersistenceResponse(success=True, count=int(count or 0))


@router.post("/{domain}/{model_name}", response_model=PersistenceResponse)
def execute_state_operation(
    domain: str,
    model_name: str,
    body: PersistenceRequest,
) -> PersistenceResponse:
    """Execute one state operation on one service-owned domain model."""
    model_cls = _model_class(domain, model_name)
    operation = body.operation.lower().strip()

    if operation == "query":
        return _query_records(model_cls, body)
    if operation == "create":
        return _create_record(model_cls, body)
    if operation == "get_or_create":
        return _get_or_create_record(model_cls, body)
    if operation == "merge":
        return _merge_record(model_cls, body)
    if operation == "update":
        return _update_record(model_cls, body)
    if operation == "update_by":
        return _update_by(model_cls, body)
    if operation == "delete":
        return _delete_record(model_cls, body)
    if operation == "delete_all":
        return _delete_all(model_cls)

    raise HTTPException(status_code=400, detail="Unsupported operation")