"""HTTP bridge BaseManager -- delegates database calls to the API.

Used by ``services`` and ``src/airunner`` (GUI) layers which do NOT
have direct database access.  Registered as the ``objects`` factory by::

    from airunner_model.base import set_objects_factory
    from airunner_model.bridge_manager import BridgeBaseManager
    set_objects_factory(BridgeBaseManager)

The bridge manager translates every ORM method into an HTTP POST to
the API service's ``/api/v1/models/{ModelName}`` persistence endpoint.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional, TypeVar

import requests

from airunner_model.settings import AIRUNNER_LOG_LEVEL
from airunner_model.utils.application import get_logger

_T = TypeVar("_T", bound=Any)

# The API URL can be overridden via environment for testing.
_API_BASE_URL = os.environ.get(
    "AIRUNNER_API_URL",
    "http://127.0.0.1:8188",
)


class BridgeBaseManager:
    """Generic persistence bridge over HTTP.

    Each instance is bound to one model class name and translates
    the standard ``BaseManager`` call signatures into HTTP requests.
    """

    def __init__(self, cls):
        self.cls = cls
        self._model_name = cls.__name__
        self.logger = get_logger(cls.__name__, AIRUNNER_LOG_LEVEL)

    # ------------------------------------------------------------------
    # Internal HTTP helpers
    # ------------------------------------------------------------------
    def _request(self, body: Dict[str, Any]) -> Dict[str, Any]:
        """Send one persistence request and return the JSON response."""
        url = f"{_API_BASE_URL}/api/v1/models/{self._model_name}"
        try:
            response = requests.post(url, json=body, timeout=30.0)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as exc:
            self.logger.error(
                "Bridge request failed for %s: %s",
                self._model_name,
                exc,
            )
            return {"record": None, "records": [], "success": False}

    def _record_to_dataclass(self, record: Optional[Dict]) -> Optional[Any]:
        """Hydrate one dict response into a model dataclass."""
        if not record:
            return None
        dataclass_cls = self.cls.get_dataclass()
        # Filter to keys the dataclass expects
        expected = {f.name for f in dataclass_cls.__dataclass_fields__.values()}
        return dataclass_cls(**{k: v for k, v in record.items() if k in expected})

    # ------------------------------------------------------------------
    # Query methods
    # ------------------------------------------------------------------
    def first(self, eager_load: Optional[List[str]] = None) -> Optional[_T]:
        """Return the first row as a dataclass, or None."""
        return self._record_to_dataclass(
            self._request({
                "operation": "query",
                "first": True,
                "eager_load": eager_load or [],
            }).get("record")
        )

    def get(self, pk, eager_load: Optional[List[str]] = None) -> Optional[_T]:
        """Return one row by primary key, or None."""
        return self._record_to_dataclass(
            self._request({
                "operation": "query",
                "pk": pk,
                "eager_load": eager_load or [],
            }).get("record")
        )

    def all(self) -> List[_T]:
        """Return all rows converted to dataclasses."""
        response = self._request({"operation": "query"})
        records = response.get("records") or []
        return [d for record in records if (d := self._record_to_dataclass(record)) is not None]

    def filter_by(self, **kwargs) -> Optional[List[_T]]:
        """Return rows matching simple equality filters."""
        response = self._request({
            "operation": "query",
            "filters": kwargs,
        })
        records = response.get("records") or []
        return [d for record in records if (d := self._record_to_dataclass(record)) is not None]

    def filter_first(self, *args) -> Optional[_T]:
        """Return the first row matching arbitrary filter expressions."""
        expressions = self._expressions_to_dicts(args)
        return self._record_to_dataclass(
            self._request({
                "operation": "query",
                "first": True,
                "expressions": expressions,
            }).get("record")
        )

    def filter(self, *args) -> Optional[List[_T]]:
        """Return all rows matching arbitrary filter expressions."""
        expressions = self._expressions_to_dicts(args)
        response = self._request({
            "operation": "query",
            "expressions": expressions,
        })
        records = response.get("records") or []
        return [d for record in records if (d := self._record_to_dataclass(record)) is not None]

    def filter_by_first(
        self, eager_load: Optional[List[str]] = None, **kwargs
    ) -> Optional[_T]:
        """Return the first row matching equality filters with eager loads."""
        return self._record_to_dataclass(
            self._request({
                "operation": "query",
                "first": True,
                "filters": kwargs,
                "eager_load": eager_load or [],
            }).get("record")
        )

    def order_by(self, *args) -> Optional[List[_T]]:
        """Return rows in a specified order."""
        clauses = [
            {"field": str(arg), "direction": "asc"}
            for arg in args
        ]
        response = self._request({
            "operation": "query",
            "order_by": clauses,
        })
        records = response.get("records") or []
        return [d for record in records if (d := self._record_to_dataclass(record)) is not None]

    def options(self, *args) -> Optional[List[_T]]:
        """Return all rows (loader options are not supported via bridge)."""
        return self.all()

    # ------------------------------------------------------------------
    # Mutation methods
    # ------------------------------------------------------------------
    def create(self, **kwargs) -> Optional[_T]:
        """Create one record and return its detached dataclass form."""
        return self._record_to_dataclass(
            self._request({
                "operation": "create",
                "values": kwargs,
            }).get("record")
        )

    def get_or_create(self, defaults: Optional[dict] = None, **kwargs) -> Any:
        """Get an existing record or create a new one."""
        response = self._request({
            "operation": "get_or_create",
            "filters": kwargs,
            "defaults": defaults or {},
        })
        return self._record_to_dataclass(response.get("record"))

    def update(self, pk=None, **kwargs) -> bool:
        """Update one record by id and return whether it succeeded."""
        record_id = kwargs.pop("pk", pk)
        response = self._request({
            "operation": "update",
            "pk": record_id,
            "values": kwargs,
        })
        return response.get("success", False)

    def delete_all(self) -> int:
        """Delete all rows and return the count removed."""
        response = self._request({"operation": "delete_all"})
        return response.get("count", 0)

    def delete_by(self, **kwargs) -> bool:
        """Delete rows matching equality filters."""
        response = self._request({
            "operation": "delete",
            "filters": kwargs,
        })
        return response.get("success", False)

    # ------------------------------------------------------------------
    # Instance-level operations (called by BaseModel.save/delete)
    # ------------------------------------------------------------------
    def save(self, instance) -> bool:
        """Persist an instance by merging it through the API."""
        values = instance.to_dict()
        response = self._request({
            "operation": "merge",
            "values": values,
        })
        return response.get("record") is not None

    def delete_instance(self, instance) -> bool:
        """Delete an instance by its primary key."""
        pk = getattr(instance, "id", None)
        if pk is None:
            return False
        response = self._request({
            "operation": "delete",
            "pk": pk,
        })
        return response.get("success", False)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _expressions_to_dicts(args) -> List[Dict[str, Any]]:
        """Convert SQLAlchemy filter expressions to dict form."""
        result = []
        for arg in args:
            if hasattr(arg, "left") and hasattr(arg, "right"):
                left = arg.left
                right = arg.right.value if hasattr(arg.right, "value") else arg.right
                field = left.key if hasattr(left, "key") else str(left)
                op_name = arg.__class__.__name__.lower()
                result.append({
                    "field": field,
                    "operator": op_name,
                    "value": right,
                })
        return result


__all__ = ["BridgeBaseManager"]
