"""GUI model manager that persists through daemon state clients."""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional

from sqlalchemy.inspection import inspect as sqlalchemy_inspect

from airunner.daemon_client.gui_daemon_client import GuiDaemonClient
from airunner.daemon_client.state_client import (
    CatalogStateClient,
    LibraryStateClient,
    SettingsStateClient,
    WorkspaceStateClient,
)


_SETTINGS_MODELS = {
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
}
_CATALOG_MODELS = {
    "AIModels",
    "ControlnetModel",
    "Embedding",
    "FineTunedModel",
    "ImageFilter",
    "ImageFilterValue",
    "Lora",
    "PipelineModel",
    "Schedulers",
}
_LIBRARY_MODELS = {"Document", "ZimFile"}
_WORKSPACE_MODELS = {
    "AgentConfig",
    "DecisionMemory",
    "LLMTool",
    "ProgressEntry",
    "ProjectFeature",
    "ProjectState",
    "SessionState",
}


class _RemoteQuery:
    """Very small query-like wrapper for `.order_by(...).all()` callers."""

    def __init__(
        self,
        manager: "GuiStateBaseManager",
        *,
        expressions: Optional[List[Dict[str, Any]]] = None,
        order_by: Optional[List[Dict[str, Any]]] = None,
        eager_load: Optional[List[str]] = None,
    ) -> None:
        self._manager = manager
        self._expressions = list(expressions or [])
        self._order_by = list(order_by or [])
        self._eager_load = list(eager_load or [])

    def all(self) -> List[Any]:
        payload = self._manager._client().execute(
            self._manager.cls.__name__,
            operation="query",
            expressions=self._expressions,
            order_by=self._order_by,
            eager_load=self._eager_load,
        )
        return self._manager._records(payload.get("records", []))

    def first(self) -> Optional[Any]:
        payload = self._manager._client().execute(
            self._manager.cls.__name__,
            operation="query",
            first=True,
            expressions=self._expressions,
            order_by=self._order_by,
            eager_load=self._eager_load,
        )
        return self._manager._record(payload.get("record"))


class GuiStateBaseManager:
    """Proxy one model's CRUD calls through daemon state domains."""

    _daemon_client: Optional[GuiDaemonClient] = None
    _clients: Dict[str, Any] = {}

    def __init__(self, cls) -> None:
        self.cls = cls

    @classmethod
    def _shared_client(cls) -> GuiDaemonClient:
        if cls._daemon_client is None:
            cls._daemon_client = GuiDaemonClient()
        return cls._daemon_client

    @classmethod
    def _domain_client(cls, domain: str):
        client = cls._clients.get(domain)
        if client is not None:
            return client
        daemon_client = cls._shared_client()
        factories = {
            "settings": SettingsStateClient,
            "catalog": CatalogStateClient,
            "library": LibraryStateClient,
            "workspace": WorkspaceStateClient,
        }
        client = factories[domain](daemon_client)
        cls._clients[domain] = client
        return client

    def _client(self):
        name = self.cls.__name__
        if name in _SETTINGS_MODELS:
            return self._domain_client("settings")
        if name in _CATALOG_MODELS:
            return self._domain_client("catalog")
        if name in _LIBRARY_MODELS:
            return self._domain_client("library")
        if name in _WORKSPACE_MODELS:
            return self._domain_client("workspace")
        raise RuntimeError(f"Unsupported daemon state model: {name}")

    def _record(self, payload: Optional[Dict[str, Any]]) -> Optional[Any]:
        if not payload:
            return None
        mapper = sqlalchemy_inspect(self.cls).mapper
        column_names = {column.key for column in mapper.column_attrs}
        record = self.cls(**{
            key: value for key, value in payload.items() if key in column_names
        })
        for relation_name, relation in mapper.relationships.items():
            if relation_name not in payload:
                continue
            relation_value = payload[relation_name]
            if relation_value is None:
                setattr(record, relation_name, None)
                continue
            related_cls = relation.entity.class_
            if relation.uselist:
                setattr(
                    record,
                    relation_name,
                    [
                        related_cls(**item)
                        for item in relation_value
                        if isinstance(item, dict)
                    ],
                )
                continue
            if isinstance(relation_value, dict):
                setattr(record, relation_name, related_cls(**relation_value))
        return record

    def _records(self, payloads: Iterable[Dict[str, Any]]) -> List[Any]:
        return [
            record
            for payload in payloads
            if (record := self._record(payload)) is not None
        ]

    @staticmethod
    def _expressions_to_dicts(args) -> List[Dict[str, Any]]:
        result = []
        for arg in args:
            if not hasattr(arg, "left") or not hasattr(arg, "right"):
                continue
            left = arg.left
            right = arg.right.value if hasattr(arg.right, "value") else arg.right
            operator = getattr(getattr(arg, "operator", None), "__name__", "eq")
            field = getattr(left, "key", str(left).split(".")[-1])
            result.append(
                {
                    "field": field,
                    "operator": operator.lower(),
                    "value": right,
                }
            )
        return result

    @staticmethod
    def _order_clauses(args) -> List[Dict[str, Any]]:
        clauses = []
        for arg in args:
            text = str(arg)
            direction = "desc" if text.upper().endswith(" DESC") else "asc"
            field = text.split()[0].split(".")[-1].strip('"')
            clauses.append({"field": field, "direction": direction})
        return clauses

    def get(self, pk, eager_load: Optional[List[str]] = None):
        payload = self._client().execute(
            self.cls.__name__,
            operation="query",
            pk=pk,
            eager_load=eager_load,
        )
        return self._record(payload.get("record"))

    def first(self, eager_load: Optional[List[str]] = None):
        payload = self._client().execute(
            self.cls.__name__,
            operation="query",
            first=True,
            eager_load=eager_load,
        )
        return self._record(payload.get("record"))

    def get_or_create(self, defaults: Optional[dict] = None, **kwargs):
        payload = self._client().execute(
            self.cls.__name__,
            operation="get_or_create",
            defaults=defaults,
            filters=kwargs,
        )
        return self._record(payload.get("record"))

    def create(self, **kwargs):
        payload = self._client().execute(
            self.cls.__name__,
            operation="create",
            values=kwargs,
        )
        return self._record(payload.get("record"))

    def update(self, pk=None, **kwargs) -> bool:
        record_id = kwargs.pop("pk", pk)
        payload = self._client().execute(
            self.cls.__name__,
            operation="update",
            pk=record_id,
            values=kwargs,
        )
        return bool(payload.get("success"))

    def update_by(self, filters: Dict[str, Any], **kwargs) -> bool:
        payload = self._client().execute(
            self.cls.__name__,
            operation="update_by",
            filters=filters,
            values=kwargs,
        )
        return bool(payload.get("success"))

    def all(self) -> List[Any]:
        payload = self._client().execute(self.cls.__name__, operation="query")
        return self._records(payload.get("records", []))

    def filter_by(self, **kwargs):
        payload = self._client().execute(
            self.cls.__name__,
            operation="query",
            filters=kwargs,
        )
        return self._records(payload.get("records", []))

    def filter_first(self, *args):
        payload = self._client().execute(
            self.cls.__name__,
            operation="query",
            first=True,
            expressions=self._expressions_to_dicts(args),
        )
        return self._record(payload.get("record"))

    def filter(self, *args):
        payload = self._client().execute(
            self.cls.__name__,
            operation="query",
            expressions=self._expressions_to_dicts(args),
        )
        return self._records(payload.get("records", []))

    def filter_by_first(
        self,
        eager_load: Optional[List[str]] = None,
        **kwargs,
    ):
        payload = self._client().execute(
            self.cls.__name__,
            operation="query",
            first=True,
            filters=kwargs,
            eager_load=eager_load,
        )
        return self._record(payload.get("record"))

    def order_by(self, *args):
        return _RemoteQuery(self, order_by=self._order_clauses(args))

    def options(self, *args):
        return _RemoteQuery(self)

    def delete(self, pk=None, **kwargs) -> bool:
        payload = self._client().execute(
            self.cls.__name__,
            operation="delete",
            pk=pk,
            filters=kwargs,
        )
        return bool(payload.get("success"))

    def delete_all(self) -> int:
        payload = self._client().execute(self.cls.__name__, operation="delete_all")
        return int(payload.get("count") or 0)

    def delete_by(self, **kwargs) -> bool:
        return self.delete(**kwargs)

    def save(self, instance) -> bool:
        payload = self._client().execute(
            self.cls.__name__,
            operation="merge",
            values=instance.to_dict(),
        )
        record = payload.get("record")
        if not isinstance(record, dict):
            return False
        for key, value in record.items():
            if hasattr(instance, key):
                setattr(instance, key, value)
        return True

    def merge(self, instance) -> bool:
        return self.save(instance)

    def delete_instance(self, instance) -> bool:
        return self.delete(getattr(instance, "id", None))