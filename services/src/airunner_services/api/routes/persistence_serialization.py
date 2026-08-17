"""Serialization helpers for daemon-backed persistence routes."""

from __future__ import annotations

import base64
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import DateTime, LargeBinary
from sqlalchemy.inspection import inspect as sqlalchemy_inspect

from airunner_services.database.secret_store import (
    MODEL_SECRET_COLUMNS,
    clear_secret,
    retrieve_secret,
    store_secret,
)


def _safe_value(value: Any, column_type: Any) -> Any:
    """Base64-encode large binary columns for JSON-safe transport."""
    if value is None:
        return None
    if isinstance(column_type, LargeBinary):
        if isinstance(value, (bytes, bytearray, memoryview)):
            return base64.b64encode(bytes(value)).decode("ascii")
    return value


def column_payload(record: Any) -> Dict[str, Any]:
    """Return mapped column values for one ORM record."""
    mapper = sqlalchemy_inspect(record).mapper
    return {
        column.key: _safe_value(
            getattr(record, column.key),
            column.columns[0].type,
        )
        for column in mapper.column_attrs
    }


def serialize_record(
    record: Any,
    *,
    eager_load: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Serialize one ORM record for GUI model hydration.

    Credential columns are decrypted from the OS keyring (when available) so
    the plaintext key is never persisted in the database.
    """
    payload = column_payload(record)
    secret_columns = MODEL_SECRET_COLUMNS.get(
        type(record).__name__, set()
    )
    for secret_column in secret_columns:
        if secret_column in payload:
            payload[secret_column] = retrieve_secret(
                secret_column,
                str(payload[secret_column] or ""),
            )
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
                column_payload(item) for item in relationship_value
            ]
            continue
        payload[relationship_name] = column_payload(relationship_value)
    return payload


def normalized_values(
    model_cls: type[Any],
    values: Dict[str, Any],
) -> Dict[str, Any]:
    """Convert serialized payload values into ORM-ready Python values.

    Credential columns are moved into the OS keyring; the database column
    stores only a reference (or the plaintext fallback when no keyring
    backend is available).
    """
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

    secret_columns = MODEL_SECRET_COLUMNS.get(
        model_cls.__name__, set()
    )
    for secret_column in secret_columns:
        if secret_column not in normalized:
            continue
        raw_value = normalized[secret_column]
        if raw_value:
            normalized[secret_column] = store_secret(
                secret_column,
                str(raw_value),
            )
        else:
            normalized[secret_column] = clear_secret(
                secret_column,
                str(raw_value or ""),
            )
    return normalized