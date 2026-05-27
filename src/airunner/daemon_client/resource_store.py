"""Daemon-backed resource clients and GUI record wrappers."""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional

from airunner.contract_enums import AvailableLanguage, CanvasToolName
from airunner.contract_enums import GeneratorSection
from airunner.daemon_client.gui_daemon_client import GuiDaemonClient


RESOURCE_DOMAINS = {
    "AIRunnerSettings": "settings",
    "ActiveGridSettings": "settings",
    "ApplicationSettings": "settings",
    "BrushSettings": "settings",
    "CanvasLayer": "settings",
    "Chatbot": "settings",
    "ControlnetSettings": "settings",
    "DrawingPadSettings": "settings",
    "EspeakSettings": "settings",
    "FontSetting": "settings",
    "GeneratorSettings": "settings",
    "GridSettings": "settings",
    "ImageToImageSettings": "settings",
    "LanguageSettings": "settings",
    "LLMGeneratorSettings": "settings",
    "MemorySettings": "settings",
    "MetadataSettings": "settings",
    "OpenVoiceSettings": "settings",
    "OutpaintSettings": "settings",
    "PathSettings": "settings",
    "PromptTemplate": "settings",
    "RAGSettings": "settings",
    "SavedPrompt": "settings",
    "ShortcutKeys": "settings",
    "SoundSettings": "settings",
    "STTSettings": "settings",
    "TargetDirectories": "settings",
    "TargetFiles": "settings",
    "User": "settings",
    "VoiceSettings": "settings",
    "WhisperSettings": "settings",
    "AIModels": "catalog",
    "ControlnetModel": "catalog",
    "Embedding": "catalog",
    "FineTunedModel": "catalog",
    "ImageFilter": "catalog",
    "ImageFilterValue": "catalog",
    "Lora": "catalog",
    "PipelineModel": "catalog",
    "Schedulers": "catalog",
    "Document": "library",
    "ZimFile": "library",
    "AgentConfig": "workspace",
    "DecisionMemory": "workspace",
    "LLMTool": "workspace",
    "ProgressEntry": "workspace",
    "ProjectFeature": "workspace",
    "ProjectState": "workspace",
    "SessionState": "workspace",
}

SINGLETON_RESOURCES = {
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
}

LAYER_RESOURCES = {
    "ControlnetSettings",
    "DrawingPadSettings",
    "ImageToImageSettings",
    "MetadataSettings",
    "OutpaintSettings",
}

RESOURCE_TO_TABLE = {
    "AIRunnerSettings": "airunner_settings",
    "ActiveGridSettings": "active_grid_settings",
    "AIModels": "aimodels",
    "AgentConfig": "agent_configs",
    "ApplicationSettings": "application_settings",
    "BrushSettings": "brush_settings",
    "CanvasLayer": "canvas_layer",
    "Chatbot": "chatbots",
    "ControlnetModel": "controlnet_models",
    "ControlnetSettings": "controlnet_settings",
    "DecisionMemory": "decision_memories",
    "Document": "documents",
    "DrawingPadSettings": "drawing_pad_settings",
    "Embedding": "embeddings",
    "EspeakSettings": "espeak_settings",
    "FineTunedModel": "fine_tuned_models",
    "FontSetting": "font_settings",
    "GeneratorSettings": "generator_settings",
    "GridSettings": "grid_settings",
    "ImageFilter": "image_filters",
    "ImageFilterValue": "image_filter_values",
    "ImageToImageSettings": "image_to_image_settings",
    "LanguageSettings": "language_settings",
    "LLMGeneratorSettings": "llm_generator_settings",
    "LLMTool": "llm_tool",
    "Lora": "lora",
    "MemorySettings": "memory_settings",
    "MetadataSettings": "metadata_settings",
    "OpenVoiceSettings": "openvoice_settings",
    "OutpaintSettings": "outpaint_settings",
    "PathSettings": "path_settings",
    "PipelineModel": "pipeline_models",
    "ProgressEntry": "progress_entries",
    "ProjectFeature": "project_features",
    "ProjectState": "project_states",
    "PromptTemplate": "prompt_templates",
    "RAGSettings": "rag_settings",
    "SavedPrompt": "saved_prompts",
    "Schedulers": "schedulers",
    "SessionState": "session_states",
    "ShortcutKeys": "shortcut_keys",
    "SoundSettings": "sound_settings",
    "STTSettings": "stt_settings",
    "TargetDirectories": "target_directories",
    "TargetFiles": "target_files",
    "User": "users",
    "VoiceSettings": "voice_settings",
    "WhisperSettings": "whisper_settings",
    "ZimFile": "zimfiles",
}

TABLE_TO_RESOURCE = {
    table_name: resource_name
    for resource_name, table_name in RESOURCE_TO_TABLE.items()
}

_shared_resource_store: "GuiResourceStore" | None = None

_APPLICATION_LOCAL_DEFAULTS = {
    "active_grid_size_lock": False,
    "current_layer_index": 0,
    "paths_initialized": False,
    "resize_on_paste": True,
    "image_to_new_layer": True,
    "dark_mode_enabled": True,
    "override_system_theme": True,
    "latest_version_check": True,
    "current_tool": CanvasToolName.BRUSH.value,
    "show_active_image_area": True,
    "generator_section": GeneratorSection.TXT2IMG.value,
    "is_maximized": False,
    "pivot_point_x": 0,
    "pivot_point_y": 0,
    "run_setup_wizard": True,
    "download_wizard_completed": False,
    "stable_diffusion_agreement_checked": True,
    "airunner_agreement_checked": True,
    "user_agreement_checked": True,
    "age_agreement_checked": True,
    "llama_license_agreement_checked": True,
}

_APPLICATION_LOCAL_GROUPS = {
    "is_maximized": "window_settings",
}


def _qsettings_value(
    key: str,
    default: Any,
    *,
    group: str,
    value_type: type | None = None,
) -> Any:
    """Read one value from QSettings when available."""
    try:
        from airunner.utils.settings.get_qsettings import get_qsettings

        settings = get_qsettings()
        settings.beginGroup(group)
        value = settings.value(key, default)
        settings.endGroup()
        if value_type is not None and value is not None:
            return value_type(value)
        return value
    except Exception:
        return default


def _set_qsettings_value(key: str, value: Any, *, group: str) -> None:
    """Write one value to QSettings when available."""
    try:
        from airunner.utils.settings.get_qsettings import get_qsettings

        settings = get_qsettings()
        settings.beginGroup(group)
        settings.setValue(key, value)
        settings.endGroup()
        settings.sync()
    except Exception:
        return


class ResourceRecord:
    """Plain attribute object for one daemon-backed resource payload."""

    def __init__(
        self,
        resource_name: str,
        values: Optional[Dict[str, Any]] = None,
    ) -> None:
        object.__setattr__(self, "resource_name", resource_name)
        object.__setattr__(self, "_values", {})
        for key, value in dict(values or {}).items():
            self._values[key] = self._wrap_value(value)

    def __getattr__(self, name: str) -> Any:
        try:
            return self._values[name]
        except KeyError as exc:
            raise AttributeError(name) from exc

    def __setattr__(self, name: str, value: Any) -> None:
        if name in {"resource_name", "_values"}:
            object.__setattr__(self, name, value)
            return
        self._values[name] = self._wrap_value(value)

    def to_dict(self) -> Dict[str, Any]:
        """Return one plain dict representation of the record."""
        return {
            key: self._unwrap_value(value)
            for key, value in self._values.items()
        }

    def _wrap_value(self, value: Any) -> Any:
        if isinstance(value, ResourceRecord):
            return value
        if isinstance(value, dict) and "id" in value:
            return ResourceRecord("__embedded__", value)
        if isinstance(value, list):
            return [self._wrap_value(item) for item in value]
        return value

    def _unwrap_value(self, value: Any) -> Any:
        if isinstance(value, ResourceRecord):
            return value.to_dict()
        if isinstance(value, list):
            return [self._unwrap_value(item) for item in value]
        return value


class DomainResourceClient:
    """HTTP client for one daemon resource domain."""

    def __init__(self, daemon_client: GuiDaemonClient, domain: str) -> None:
        self._client = daemon_client
        self._domain = domain

    def get_singleton(
        self,
        resource_name: str,
        *,
        create_if_missing: bool = True,
    ) -> Dict[str, Any]:
        response = self._client._request(
            "GET",
            (
                f"/api/v1/{self._domain}/resources/{resource_name}/singleton"
                f"?create_if_missing={'true' if create_if_missing else 'false'}"
            ),
        )
        return response.json()

    def update_singleton(
        self,
        resource_name: str,
        values: Dict[str, Any],
    ) -> Dict[str, Any]:
        response = self._client._request(
            "PUT",
            f"/api/v1/{self._domain}/resources/{resource_name}/singleton",
            json_payload={"values": dict(values or {})},
        )
        return response.json()

    def get_layer(
        self,
        resource_name: str,
        layer_id: int,
        *,
        create_if_missing: bool = True,
    ) -> Dict[str, Any]:
        response = self._client._request(
            "GET",
            (
                f"/api/v1/{self._domain}/resources/{resource_name}/"
                f"layers/{layer_id}?create_if_missing="
                f"{'true' if create_if_missing else 'false'}"
            ),
        )
        return response.json()

    def update_layer(
        self,
        resource_name: str,
        layer_id: int,
        values: Dict[str, Any],
    ) -> Dict[str, Any]:
        response = self._client._request(
            "PUT",
            f"/api/v1/{self._domain}/resources/{resource_name}/layers/{layer_id}",
            json_payload={"values": dict(values or {})},
        )
        return response.json()

    def query(
        self,
        resource_name: str,
        *,
        filters: Optional[Dict[str, Any]] = None,
        order_by: Optional[List[Dict[str, str]]] = None,
        eager_load: Optional[List[str]] = None,
        limit: Optional[int] = None,
    ) -> Dict[str, Any]:
        response = self._client._request(
            "POST",
            f"/api/v1/{self._domain}/resources/{resource_name}/query",
            json_payload={
                "filters": dict(filters or {}),
                "order_by": list(order_by or []),
                "eager_load": list(eager_load or []),
                "limit": limit,
            },
        )
        return response.json()

    def first(
        self,
        resource_name: str,
        *,
        filters: Optional[Dict[str, Any]] = None,
        order_by: Optional[List[Dict[str, str]]] = None,
        eager_load: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        response = self._client._request(
            "POST",
            f"/api/v1/{self._domain}/resources/{resource_name}/first",
            json_payload={
                "filters": dict(filters or {}),
                "order_by": list(order_by or []),
                "eager_load": list(eager_load or []),
            },
        )
        return response.json()

    def get(self, resource_name: str, record_id: int) -> Dict[str, Any]:
        response = self._client._request(
            "GET",
            f"/api/v1/{self._domain}/resources/{resource_name}/{record_id}",
        )
        return response.json()

    def create(
        self,
        resource_name: str,
        values: Dict[str, Any],
    ) -> Dict[str, Any]:
        response = self._client._request(
            "POST",
            f"/api/v1/{self._domain}/resources/{resource_name}",
            json_payload={"values": dict(values or {})},
        )
        return response.json()

    def update(
        self,
        resource_name: str,
        record_id: int,
        values: Dict[str, Any],
    ) -> Dict[str, Any]:
        response = self._client._request(
            "PUT",
            f"/api/v1/{self._domain}/resources/{resource_name}/{record_id}",
            json_payload={"values": dict(values or {})},
        )
        return response.json()

    def delete(self, resource_name: str, record_id: int) -> Dict[str, Any]:
        response = self._client._request(
            "DELETE",
            f"/api/v1/{self._domain}/resources/{resource_name}/{record_id}",
        )
        return response.json()

    def delete_many(
        self,
        resource_name: str,
        *,
        filters: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        response = self._client._request(
            "POST",
            f"/api/v1/{self._domain}/resources/{resource_name}/delete",
            json_payload={"filters": dict(filters or {})},
        )
        return response.json()


class GuiResourceStore:
    """Domain-aware resource store for GUI persistence consumers."""

    def __init__(self, daemon_client: Optional[GuiDaemonClient] = None) -> None:
        shared_client = daemon_client or GuiDaemonClient()
        self._clients = {
            "settings": DomainResourceClient(shared_client, "settings"),
            "catalog": DomainResourceClient(shared_client, "catalog"),
            "library": DomainResourceClient(shared_client, "library"),
            "workspace": DomainResourceClient(shared_client, "workspace"),
        }

    def new_record(
        self,
        resource_name: str,
        values: Optional[Dict[str, Any]] = None,
    ) -> ResourceRecord:
        """Return a plain record wrapper for one resource name."""
        return ResourceRecord(resource_name, values)

    def is_singleton(self, resource_name: str) -> bool:
        """Return whether one resource is singleton-scoped."""
        return resource_name in SINGLETON_RESOURCES

    def is_layer_resource(self, resource_name: str) -> bool:
        """Return whether one resource is layer-scoped."""
        return resource_name in LAYER_RESOURCES

    def get_singleton(
        self,
        resource_name: str,
        *,
        create_if_missing: bool = True,
    ) -> ResourceRecord:
        """Return one singleton record for a resource."""
        payload = self._client(resource_name).get_singleton(
            resource_name,
            create_if_missing=create_if_missing,
        )
        return self._apply_local_overlay(
            resource_name,
            self._record(resource_name, payload.get("record")),
        )

    def update_singleton(
        self,
        resource_name: str,
        values: Dict[str, Any],
    ) -> ResourceRecord:
        """Update one singleton record and return the new payload."""
        local_values, remote_values = self._split_local_values(
            resource_name,
            values,
        )
        if remote_values:
            self._client(resource_name).update_singleton(resource_name, remote_values)
        self._write_local_values(resource_name, local_values)
        return self.get_singleton(resource_name, create_if_missing=True)

    def get_layer(
        self,
        resource_name: str,
        layer_id: int,
    ) -> ResourceRecord:
        """Return one layer-scoped record."""
        payload = self._client(resource_name).get_layer(resource_name, layer_id)
        return self._record(resource_name, payload.get("record"))

    def update_layer(
        self,
        resource_name: str,
        layer_id: int,
        values: Dict[str, Any],
    ) -> ResourceRecord:
        """Update one layer-scoped record."""
        payload = self._client(resource_name).update_layer(
            resource_name,
            layer_id,
            values,
        )
        return self._record(resource_name, payload.get("record"))

    def query(
        self,
        resource_name: str,
        *,
        filters: Optional[Dict[str, Any]] = None,
        order_by: Optional[List[Dict[str, str]]] = None,
        eager_load: Optional[List[str]] = None,
        limit: Optional[int] = None,
    ) -> List[ResourceRecord]:
        """Query one collection resource."""
        payload = self._client(resource_name).query(
            resource_name,
            filters=filters,
            order_by=order_by,
            eager_load=eager_load,
            limit=limit,
        )
        return [
            self._record(resource_name, item)
            for item in payload.get("records", [])
        ]

    def first(
        self,
        resource_name: str,
        *,
        filters: Optional[Dict[str, Any]] = None,
        order_by: Optional[List[Dict[str, str]]] = None,
        eager_load: Optional[List[str]] = None,
    ) -> Optional[ResourceRecord]:
        """Return the first matching collection record."""
        payload = self._client(resource_name).first(
            resource_name,
            filters=filters,
            order_by=order_by,
            eager_load=eager_load,
        )
        return self._record(resource_name, payload.get("record"))

    def get(
        self,
        resource_name: str,
        record_id: Optional[int],
    ) -> Optional[ResourceRecord]:
        """Return one record by primary key."""
        if record_id is None:
            return None
        payload = self._client(resource_name).get(resource_name, int(record_id))
        return self._record(resource_name, payload.get("record"))

    def create(
        self,
        resource_name: str,
        values: Dict[str, Any],
    ) -> ResourceRecord:
        """Create one collection record."""
        payload = self._client(resource_name).create(resource_name, values)
        return self._record(resource_name, payload.get("record"))

    def update(
        self,
        resource_name: str,
        record_id: Optional[int],
        values: Dict[str, Any],
    ) -> Optional[ResourceRecord]:
        """Update one collection record."""
        if record_id is None:
            return None
        payload = self._client(resource_name).update(
            resource_name,
            int(record_id),
            values,
        )
        return self._record(resource_name, payload.get("record"))

    def delete(self, resource_name: str, record_id: Optional[int]) -> bool:
        """Delete one collection record by primary key."""
        if record_id is None:
            return False
        payload = self._client(resource_name).delete(resource_name, int(record_id))
        return bool(payload.get("deleted"))

    def delete_many(
        self,
        resource_name: str,
        *,
        filters: Optional[Dict[str, Any]] = None,
    ) -> int:
        """Delete many records for one resource."""
        payload = self._client(resource_name).delete_many(
            resource_name,
            filters=filters,
        )
        return int(payload.get("count") or 0)

    def _client(self, resource_name: str) -> DomainResourceClient:
        """Return the domain client that owns one resource."""
        domain = RESOURCE_DOMAINS.get(resource_name)
        if domain is None:
            raise RuntimeError(f"Unsupported GUI resource: {resource_name}")
        return self._clients[domain]

    def _record(
        self,
        resource_name: str,
        payload: Optional[Dict[str, Any]],
    ) -> Optional[ResourceRecord]:
        """Wrap one payload as a resource record when present."""
        if not payload:
            return None
        return ResourceRecord(resource_name, payload)

    def _apply_local_overlay(
        self,
        resource_name: str,
        record: Optional[ResourceRecord],
    ) -> ResourceRecord:
        """Attach GUI-local QSettings fields to a singleton record."""
        record = record or ResourceRecord(resource_name, {})
        if resource_name == "ApplicationSettings":
            for key, default in _APPLICATION_LOCAL_DEFAULTS.items():
                group = _APPLICATION_LOCAL_GROUPS.get(key, "application_settings")
                value_type = bool if isinstance(default, bool) else int
                if isinstance(default, str):
                    value_type = str
                setattr(
                    record,
                    key,
                    _qsettings_value(
                        key,
                        default,
                        group=group,
                        value_type=value_type,
                    ),
                )
        elif resource_name == "LanguageSettings":
            record.gui_language = _qsettings_value(
                "gui_language",
                AvailableLanguage.EN.value,
                group="language",
                value_type=str,
            )
        elif resource_name == "SoundSettings":
            record.playback_device = _qsettings_value(
                "playback_device",
                "",
                group="audio_devices",
                value_type=str,
            )
            record.recording_device = _qsettings_value(
                "recording_device",
                "",
                group="audio_devices",
                value_type=str,
            )
        return record

    def _split_local_values(
        self,
        resource_name: str,
        values: Dict[str, Any],
    ) -> tuple[Dict[str, Any], Dict[str, Any]]:
        """Split one update payload into GUI-local and daemon-owned values."""
        local_values: Dict[str, Any] = {}
        remote_values: Dict[str, Any] = {}
        local_keys: set[str] = set()
        if resource_name == "ApplicationSettings":
            local_keys = set(_APPLICATION_LOCAL_DEFAULTS)
        elif resource_name == "LanguageSettings":
            local_keys = {"gui_language"}
        elif resource_name == "SoundSettings":
            local_keys = {"playback_device", "recording_device"}

        for key, value in dict(values or {}).items():
            if key in local_keys:
                local_values[key] = value
                continue
            remote_values[key] = value
        return local_values, remote_values

    def _write_local_values(
        self,
        resource_name: str,
        values: Dict[str, Any],
    ) -> None:
        """Persist GUI-local values to QSettings when required."""
        if not values:
            return
        if resource_name == "ApplicationSettings":
            for key, value in values.items():
                group = _APPLICATION_LOCAL_GROUPS.get(key, "application_settings")
                _set_qsettings_value(key, value, group=group)
        elif resource_name == "LanguageSettings":
            for key, value in values.items():
                _set_qsettings_value(key, value, group="language")
        elif resource_name == "SoundSettings":
            for key, value in values.items():
                _set_qsettings_value(key, value, group="audio_devices")


def get_resource_store() -> GuiResourceStore:
    """Return a shared process-local GUI resource store instance."""
    global _shared_resource_store
    if _shared_resource_store is None:
        _shared_resource_store = GuiResourceStore()
    return _shared_resource_store


__all__ = [
    "GuiResourceStore",
    "get_resource_store",
    "LAYER_RESOURCES",
    "RESOURCE_DOMAINS",
    "RESOURCE_TO_TABLE",
    "ResourceRecord",
    "SINGLETON_RESOURCES",
    "TABLE_TO_RESOURCE",
]