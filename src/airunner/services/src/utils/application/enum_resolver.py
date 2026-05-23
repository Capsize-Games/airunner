"""Helpers for resolving enum members without direct GUI imports."""

from __future__ import annotations

from enum import Enum, auto
from typing import Any, Mapping

from airunner_services.contract_enums import LLMActionType as SharedLLMActionType
from airunner_services.contract_enums import SignalCode as SharedSignalCode


_SERVICE_SIGNAL_DEFAULTS: dict[str, str] = {
    "AI_MODELS_SAVE_OR_UPDATE_SIGNAL": "ai_models_save_or_update_signal",
    "APPLICATION_ACTIVE_GRID_AREA_UPDATED": "active_grid_area_updated",
    "APPLICATION_STOP_SD_PROGRESS_BAR_SIGNAL": (
        "stop_image_generator_progress_bar_signal"
    ),
    "ART_MODEL_DOWNLOAD_REQUIRED": "art_model_download_required",
    "CANCEL_HUGGINGFACE_DOWNLOAD": "cancel_huggingface_download",
    "CHANGE_SCHEDULER_SIGNAL": "change_scheduler_signal",
    "CHATBOT_CHANGED": "chatbot_changed_signal",
    "DELETE_MESSAGES_AFTER_ID": "delete_messages_after_id",
    "DOCUMENT_COLLECTION_CHANGED": "document_collection_changed_signal",
    "DOCUMENT_INDEXED": "document_indexed_signal",
    "DOCUMENT_INDEX_FAILED": "document_index_failed_signal",
    "GENERATOR_FORM_UPDATE_VALUES_SIGNAL": "generator_form_update_values",
    "IMAGE_EXPORTED": "image_exported_signal",
    "KNOWLEDGE_FACT_ADDED": "knowledge_fact_added_signal",
    "LAYERS_SHOW_SIGNAL": "show_layers_signal",
    "LLM_CONVERT_TO_GGUF_SIGNAL": "llm_convert_to_gguf_signal",
    "LLM_IMAGE_PROMPT_GENERATED_SIGNAL": (
        "llm_image_prompt_generated_signal"
    ),
    "LLM_MODEL_CHANGED": "llm_model_changed_signal",
    "LLM_MODEL_DOWNLOAD_REQUIRED": "llm_model_download_required",
    "LLM_QUANTIZATION_COMPLETE": "llm_quantization_complete",
    "LLM_QUANTIZATION_FAILED": "llm_quantization_failed",
    "LLM_QUANTIZATION_PROGRESS": "llm_quantization_progress",
    "LLM_TEXT_GENERATE_REQUEST_SIGNAL": (
        "llm_text_generate_request_signal"
    ),
    "LLM_TEXT_STREAMED_SIGNAL": "llm_text_streamed_signal",
    "LLM_TEXT_STREAM_PROCESS_SIGNAL": "llm_text_stream_process_signal",
    "MISSING_REQUIRED_MODELS": "missing_required_models",
    "MOOD_SUMMARY_UPDATE_STARTED": "mood_summary_update_started_signal",
    "QUEUE_LOAD_CONVERSATION": "queue_load_conversation_signal",
    "RAG_DOCUMENT_ADDED": "rag_document_added_signal",
    "RAG_INDEXING_COMPLETE": "rag_indexing_complete_signal",
    "RAG_INDEXING_PROGRESS": "rag_indexing_progress_signal",
    "RAG_RELOAD_INDEX_SIGNAL": "rag_reload_index_signal",
    "SAFETY_CHECKER_FILTER_COMPLETE": "safety_checker_filter_complete",
    "SAFETY_CHECKER_FILTER_REQUEST": "safety_checker_filter_request",
    "SAFETY_CHECKER_UNLOAD_SIGNAL": "safety_checker_unload_signal",
    "SD_LOAD_PROMPT_SIGNAL": "load_saved_stablediffuion_prompt_signal",
    "SD_PIPELINE_LOADED_SIGNAL": "sd_pipeline_loaded_signal",
    "SD_SAVE_PROMPT_SIGNAL": "save_stablediffusion_prompt_signal",
    "SD_UPDATE_BATCH_IMAGES_SIGNAL": "sd_update_batch_images_signal",
    "START_HUGGINGFACE_DOWNLOAD": "start_huggingface_download",
    "STT_START_CAPTURE_SIGNAL": "stt_start_capture",
    "STT_STOP_CAPTURE_SIGNAL": "stt_stop_capture",
    "TOGGLE_LLM_SIGNAL": "toggle_llm_signal",
    "TTS_GENERATOR_WORKER_ADD_TO_STREAM_SIGNAL": (
        "TTSGeneratorWorker_add_to_stream_signal"
    ),
    "UPSCALE_COMPLETED": "upscale_completed_signal",
    "UPSCALE_FAILED": "upscale_failed_signal",
    "UPSCALE_PROGRESS": "upscale_progress_signal",
}


def signal_code_member(name: str, default: Any = None) -> Any:
    """Return one signal code from shared enums or service defaults."""
    shared_signal = getattr(SharedSignalCode, name, None)
    if shared_signal is not None:
        return shared_signal
    service_signal = _SERVICE_SIGNAL_DEFAULTS.get(name)
    if service_signal is not None:
        return service_signal
    if default is not None:
        return default
    raise AttributeError(f"SignalCode has no member {name}")


class SignalCodeProxy:
    """Resolve signal codes lazily with optional service-owned defaults."""

    def __init__(
        self,
        defaults: Mapping[str, Any] | None = None,
    ) -> None:
        self._defaults = dict(defaults or {})

    def __getattr__(self, name: str) -> Any:
        return signal_code_member(name, self._defaults.get(name))


def signal_code_proxy(
    defaults: Mapping[str, Any] | None = None,
) -> SignalCodeProxy:
    """Return one lazy signal-code proxy for module-level use."""
    return SignalCodeProxy(defaults)


def llm_action_type() -> Any:
    """Return the shared LLM action type enum."""
    return SharedLLMActionType


class _ModelActionFallback(Enum):
    NONE = auto()
    LOAD = auto()
    UNLOAD = auto()
    CLEAR = auto()
    APPLY_TO_PIPE = auto()
    GENERATE = auto()


def model_action_type() -> Any:
    """Return the service-owned model action enum."""
    return _ModelActionFallback


class _HandlerStateFallback(Enum):
    UNINITIALIZED = "Uninitialized"
    INITIALIZED = "Initialized"
    LOADING = "Loading"
    READY = "Ready"
    GENERATING = "Generating"
    PREPARING_TO_GENERATE = "Preparing to Generate"
    ERROR = "Error"


def handler_state_type() -> Any:
    """Return the service-owned handler state enum."""
    return _HandlerStateFallback


__all__ = [
    "SignalCodeProxy",
    "handler_state_type",
    "llm_action_type",
    "model_action_type",
    "signal_code_member",
    "signal_code_proxy",
]