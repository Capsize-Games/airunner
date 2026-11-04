"""Local fallback runtime clients backed by existing signal services."""

from __future__ import annotations

import base64
import io
import os
import threading
from queue import Empty, Queue
from typing import Any, Callable, Iterable, Optional

from PIL import Image

from airunner_services.ipc.messages import (
    EnvelopeStatus,
    ErrorEnvelope,
    RequestEnvelope,
    ResponseEnvelope,
    StreamDelta,
)
from airunner_services.runtimes.base import RuntimeClient
from airunner_services.runtimes.contracts import (
    ArtInvocationRequest,
    LLMInvocationRequest,
    RuntimeAction,
    RuntimeKind,
    RuntimeMode,
    RuntimeHealthStatus,
    TTSInvocationRequest,
)
from airunner_services.runtimes.registry import RuntimeRegistry, RuntimeRoute
from airunner_services.runtimes.art_daemon_runtime_settings import (
    resolve_art_daemon_runtime_settings,
)
from airunner_services.utils.application.get_logger import get_logger
from airunner_services.runtimes.local_fallback_art_helpers import (
    _resolve_art_active_rect,
    _resolve_art_generator_section,
    _resolve_art_operation,
    _resolve_art_pipeline_action,
    _resolve_art_request_image,
    _resolve_art_request_mask,
    _resolve_art_request_outpaint_mask_blur,
    _resolve_art_request_scheduler,
    _resolve_art_request_strength,
    _resolve_art_request_version,
)
from airunner_services.runtimes.local_fallback_stt_client import (
    MAX_LOCAL_FALLBACK_AUDIO_BYTES,
    LocalFallbackSTTClient,
    _build_stt_service,
)
from airunner_services.runtimes.signal_runtime_client import (
    DEFAULT_TIMEOUT_SECONDS,
    HealthProvider,
    LoadedModelProvider,
    _SignalRuntimeClient,
    _model_status_value,
    _resolve_model_type,
)
from airunner_services.runtimes.tts_capabilities import (
    OPENVOICE_DEFERRED_DETAILS,
    TTS_BACKEND_UNAVAILABLE_CODE,
    deferred_tts_metadata,
    is_deferred_tts_model_type,
    normalize_tts_model_type,
)
from airunner_services.runtimes.espeak_cli_renderer import (
    EspeakCliRenderer,
    EspeakRenderError,
)

logger = get_logger(__name__)

DEFAULT_PROVIDER = "local"
ProgressCallback = Callable[[dict[str, Any]], None]
_UNRESOLVED_WORKER = object()

LLMRequestFactory = Callable[[LLMInvocationRequest], Any]



def _build_llm_service() -> Any:
    """Create the default LLM API service lazily."""
    from airunner_services.api.services.llm_services import LLMAPIService

    return LLMAPIService()



def _build_tts_service() -> Any:
    """Create the default TTS API service lazily."""
    from airunner_services.api.services.tts_services import TTSAPIService

    return TTSAPIService()


def _build_art_service() -> Any:
    """Create the default art API service lazily."""
    from airunner_services.api.services.art_services import ARTAPIService

    return ARTAPIService()


def _build_llm_request(invocation: LLMInvocationRequest) -> Any:
    """Create an LLM request object for the legacy signal path."""
    from airunner_services.llm.llm_request import LLMRequest

    request = LLMRequest()
    request.temperature = invocation.temperature
    if invocation.max_tokens is not None:
        request.max_new_tokens = invocation.max_tokens
    if invocation.model:
        request.model = invocation.model
    return request



def _resolve_served_model_id(model_path: str) -> str:
    """Resolve a known local model id from one loaded model path."""
    from airunner_services.llm.provider_config import LLMProviderConfig

    resolved = LLMProviderConfig.resolve_model_id(
        "local", os.path.basename(model_path)
    )
    return resolved or ""


class LocalFallbackLLMClient(_SignalRuntimeClient):
    """Bridge LLM runtime envelopes to the existing signal service path."""

    def __init__(
        self,
        provider: str = DEFAULT_PROVIDER,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        llm_service: Any = None,
        mediator: Any = None,
        llm_request_factory: Optional[LLMRequestFactory] = None,
        health_provider: Optional[HealthProvider] = None,
        loaded_model_provider: Optional[LoadedModelProvider] = None,
    ) -> None:
        llm_service = llm_service or _build_llm_service()
        super().__init__(
            RuntimeKind.LLM,
            provider,
            signal_source=llm_service,
            mediator=mediator,
            timeout_seconds=timeout_seconds,
            health_provider=health_provider,
            allows_model_control=True,
            model_type=_resolve_model_type("LLM"),
            loaded_model_provider=loaded_model_provider,
        )
        self._llm_service = llm_service
        self._llm_request_factory = llm_request_factory or _build_llm_request

    def _probe_loaded_model(self) -> dict[str, Any]:
        """Return the model the LLM worker currently has loaded."""
        provided = super()._probe_loaded_model()
        if provided:
            return provided
        return self._worker_loaded_model()

    def _worker_loaded_model(self) -> dict[str, Any]:
        """Build served-model metadata from real worker state."""
        model_path = self._current_worker_model_path()
        if not model_path:
            return {}
        metadata: dict[str, Any] = {}
        model_id = _resolve_served_model_id(model_path)
        if model_id:
            metadata["model_id"] = model_id
        metadata["model_path"] = model_path
        return metadata

    def _current_worker_model_path(self) -> str:
        """Read the loaded path without creating a worker/manager."""
        return self._reachable_worker_model_path() or ""

    def _reachable_worker_model_path(self) -> Optional[str]:
        """Return worker path, "" if none, None if unknown.

        None is no evidence; "" proves no model is loaded."""
        manager = self._reachable_model_manager()
        if manager is None:
            return None
        missing = object()
        try:
            model_path = getattr(manager, "_current_model_path", missing)
        except Exception:
            return None
        if model_path is missing:
            return None
        if model_path is None:
            return ""
        if isinstance(model_path, str):
            return model_path.strip()
        return None

    def _reachable_model_manager(self) -> Any:
        """Return the live model manager without creating one."""
        try:
            worker_manager = getattr(
                self._signal_source, "_worker_manager", None
            )
            if callable(worker_manager):
                worker_manager = worker_manager()
            worker = getattr(
                worker_manager, "_llm_generate_worker", None
            )
            return getattr(worker, "_model_manager", None)
        except Exception:
            return None

    def _revalidate_loaded_model(self) -> None:
        """Re-check the snapshot against reachable worker state."""
        if self._loaded_model_provider is not None:
            super()._revalidate_loaded_model()
            return
        if not self._loaded_model:
            return
        model_path = self._reachable_worker_model_path()
        if model_path is None:
            return
        if not model_path:
            self._mark_silently_unloaded()
            return
        if not self._snapshot_matches(model_path):
            self._loaded_model = self._worker_loaded_model()

    def _snapshot_matches(self, model_path: str) -> bool:
        """Return True when the snapshot names this model path."""
        snapshot_path = self._loaded_model.get("model_path")
        if isinstance(snapshot_path, str) and snapshot_path:
            return snapshot_path == model_path
        snapshot_id = self._loaded_model.get("model_id")
        if isinstance(snapshot_id, str) and snapshot_id:
            return snapshot_id == _resolve_served_model_id(model_path)
        return True

    def invoke(self, request: RequestEnvelope) -> ResponseEnvelope:
        """Invoke the legacy LLM service or model-control path."""
        if request.runtime is not RuntimeKind.LLM:
            raise ValueError("LocalFallbackLLMClient only supports LLM")
        if request.action is RuntimeAction.STATUS:
            return self._status_response(request.request_id)
        if request.action is RuntimeAction.LOAD_MODEL:
            return self._load_model(request.request_id)
        if request.action is RuntimeAction.UNLOAD_MODEL:
            return self._unload_model(request.request_id)
        invocation = self._validate_request(request)
        response_queue = self._dispatch(request, invocation)
        try:
            return self._collect_response(request.request_id, response_queue)
        except TimeoutError as exc:
            return self._timeout_response(request.request_id, str(exc))
        finally:
            self._mediator.unregister_pending_request(request.request_id)

    def stream(self, request: RequestEnvelope) -> Iterable[StreamDelta]:
        """Stream deltas from the legacy LLM service."""
        invocation = self._validate_request(request)
        response_queue = self._dispatch(request, invocation)
        try:
            yield from self._stream_responses(request.request_id, response_queue)
        except TimeoutError as exc:
            yield self._failure_delta(request.request_id, str(exc))
        finally:
            self._mediator.unregister_pending_request(request.request_id)

    def cancel(self, request_id: str) -> ResponseEnvelope:
        """Interrupt the current legacy LLM request on a best-effort basis."""
        if hasattr(self._llm_service, "interrupt"):
            self._llm_service.interrupt()
        return ResponseEnvelope(
            request_id=request_id,
            status=EnvelopeStatus.CANCELLED,
            metadata={"best_effort": True},
        )

    def _validate_request(
        self, request: RequestEnvelope
    ) -> LLMInvocationRequest:
        """Validate a runtime request for this client."""
        if request.action is not RuntimeAction.INVOKE:
            raise ValueError("LocalFallbackLLMClient only supports invoke")
        return LLMInvocationRequest.model_validate(request.payload)

    def _load_model(self, request_id: str) -> ResponseEnvelope:
        """Load the local LLM through the current signal graph."""
        from airunner_common.contract_enums import ModelStatus, SignalCode

        return self._wait_for_model_status(
            request_id,
            emit_code=SignalCode.LLM_LOAD_SIGNAL,
            emit_data={},
            success_statuses=(ModelStatus.LOADED, ModelStatus.READY),
            timeout_code="llm_load_timeout",
            failure_code="llm_load_failed",
            action_name="LLM load",
        )

    def _unload_model(self, request_id: str) -> ResponseEnvelope:
        """Unload the local LLM through the current signal graph."""
        from airunner_common.contract_enums import ModelStatus, SignalCode

        return self._wait_for_model_status(
            request_id,
            emit_code=SignalCode.LLM_UNLOAD_SIGNAL,
            emit_data={},
            success_statuses=(ModelStatus.UNLOADED,),
            timeout_code="llm_unload_timeout",
            failure_code="llm_unload_failed",
            action_name="LLM unload",
        )

    def _dispatch(
        self,
        request: RequestEnvelope,
        invocation: LLMInvocationRequest,
    ) -> Queue:
        """Dispatch a request through the legacy LLM API service."""
        response_queue = self._mediator.register_pending_request(
            request.request_id
        )
        try:
            self._llm_service.send_request(
                prompt=self._prompt_from_messages(invocation),
                llm_request=self._prepare_llm_request(invocation),
                action=self._resolve_action(),
                do_tts_reply=False,
                request_id=request.request_id,
            )
        except Exception:
            self._mediator.unregister_pending_request(request.request_id)
            raise
        return response_queue

    def _prepare_llm_request(self, invocation: LLMInvocationRequest) -> Any:
        """Populate a legacy request object from the neutral contract."""
        request = self._llm_request_factory(invocation)
        system_prompt = self._system_prompt(invocation)
        if system_prompt:
            setattr(request, "system_prompt", system_prompt)
        if invocation.tool_choice and invocation.tool_choice != "auto":
            setattr(request, "force_tool", invocation.tool_choice)
        runtime_profile = invocation.metadata.get("gguf_runtime_profile")
        if isinstance(runtime_profile, str) and runtime_profile.strip():
            setattr(
                request,
                "gguf_runtime_profile",
                runtime_profile.strip(),
            )
        return request

    def _collect_response(
        self, request_id: str, response_queue: Queue
    ) -> ResponseEnvelope:
        """Collect a full response from streamed legacy chunks."""
        chunks = []
        for response in self._iter_responses(response_queue):
            chunks.append(self._response_message(response))
            if self._is_complete(response):
                return ResponseEnvelope(
                    request_id=request_id,
                    status=EnvelopeStatus.SUCCEEDED,
                    payload={"content": "".join(chunks)},
                    metadata=self._response_metadata(response),
                )
        raise TimeoutError("Timed out waiting for LLM response")

    def _stream_responses(
        self, request_id: str, response_queue: Queue
    ) -> Iterable[StreamDelta]:
        """Yield response deltas from the legacy LLM service."""
        responses = self._iter_responses(response_queue)
        for sequence, response in enumerate(responses):
            yield StreamDelta(
                request_id=request_id,
                sequence=sequence,
                delta={"content": self._response_message(response)},
                final=self._is_complete(response),
                metadata=self._response_metadata(response),
            )
            if self._is_complete(response):
                return
        raise TimeoutError("Timed out waiting for streamed LLM response")

    def _iter_responses(self, response_queue: Queue) -> Iterable[Any]:
        """Iterate over queued legacy LLM response objects."""
        while True:
            try:
                data = response_queue.get(timeout=self._timeout_seconds)
            except Empty as exc:
                raise TimeoutError(
                    "Timed out waiting for LLM response"
                ) from exc
            response = data.get("response")
            if response is not None:
                yield response

    @staticmethod
    def _prompt_from_messages(invocation: LLMInvocationRequest) -> str:
        """Extract the user-facing prompt from a message list."""
        for message in reversed(invocation.messages):
            if message.content:
                return message.content
        return ""

    @staticmethod
    def _system_prompt(invocation: LLMInvocationRequest) -> Optional[str]:
        """Extract the leading system prompt when present."""
        for message in invocation.messages:
            if message.role.value == "system" and message.content:
                return message.content
        return None

    @staticmethod
    def _response_message(response: Any) -> str:
        """Read message text from a legacy response object."""
        return getattr(response, "message", "")

    @staticmethod
    def _is_complete(response: Any) -> bool:
        """Return True when a legacy response marks completion."""
        return bool(getattr(response, "is_end_of_message", False))

    @staticmethod
    def _response_metadata(response: Any) -> dict[str, Any]:
        """Collect optional usage data from a legacy response object."""
        metadata = {}
        for field in ("tools", "prompt_tokens", "completion_tokens"):
            value = getattr(response, field, None)
            if value is not None:
                metadata[field] = value
        total_tokens = getattr(response, "total_tokens", None)
        if total_tokens is not None:
            metadata["total_tokens"] = total_tokens
        return metadata

    @staticmethod
    def _resolve_action() -> Any:
        """Resolve the legacy action enum lazily."""
        from airunner_common.contract_enums import LLMActionType

        return LLMActionType.CHAT

    @staticmethod
    def _timeout_response(request_id: str, message: str) -> ResponseEnvelope:
        """Create a timeout failure envelope."""
        return ResponseEnvelope(
            request_id=request_id,
            status=EnvelopeStatus.FAILED,
            error=ErrorEnvelope(
                code="llm_timeout",
                message=message,
                retryable=True,
            ),
        )

    @staticmethod
    def _failure_delta(request_id: str, message: str) -> StreamDelta:
        """Create a terminal error delta for streamed requests."""
        return StreamDelta(
            request_id=request_id,
            final=True,
            status=EnvelopeStatus.FAILED,
            metadata={"error": message},
        )



class LocalFallbackTTSClient(_SignalRuntimeClient):
    """Use configured headless TTS backends with opt-in legacy playback."""

    def __init__(
        self,
        provider: str = DEFAULT_PROVIDER,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        signal_source: Any = None,
        mediator: Any = None,
        health_provider: Optional[HealthProvider] = None,
        allow_legacy_playback: bool = False,
    ) -> None:
        super().__init__(
            RuntimeKind.TTS,
            provider,
            signal_source=signal_source or _build_tts_service(),
            mediator=mediator,
            timeout_seconds=timeout_seconds,
            health_provider=health_provider,
            model_type=_resolve_model_type("TTS"),
        )
        self._espeak_cli_renderer = EspeakCliRenderer()
        self._espeak_cli_ready = False
        self._allow_legacy_playback = bool(allow_legacy_playback)

    def healthcheck(self):
        """Report loaded TTS identity without creating a worker or model."""
        health = super().healthcheck()
        if self._espeak_cli_ready:
            return health.model_copy(
                update={
                    "status": RuntimeHealthStatus.READY,
                    "details": "eSpeak NG command-line renderer is ready",
                    "metadata": {
                        **health.metadata,
                        "model_type": "espeak",
                        "model_id": "espeak-ng-cli",
                        "model_name": "eSpeak NG CLI",
                        "voice_ids": list(
                            self._espeak_cli_renderer.voice_ids or ()
                        ),
                    },
                }
            )
        worker = self._existing_tts_worker()
        status_getter = getattr(worker, "_current_tts_status", None)
        if worker is None or not callable(status_getter):
            configured_model = os.environ.get("AIRUNNER_TTS_MODEL_TYPE")
            if is_deferred_tts_model_type(configured_model):
                metadata = {
                    **health.metadata,
                    **deferred_tts_metadata(configured_model),
                }
                return health.model_copy(
                    update={
                        "status": RuntimeHealthStatus.FAILED,
                        "details": OPENVOICE_DEFERRED_DETAILS,
                        "metadata": metadata,
                    }
                )
            return health

        from airunner_common.contract_enums import ModelStatus

        model_status = status_getter()
        status_map = {
            ModelStatus.LOADING: RuntimeHealthStatus.STARTING,
            ModelStatus.LOADED: RuntimeHealthStatus.READY,
            ModelStatus.READY: RuntimeHealthStatus.READY,
            ModelStatus.FAILED: RuntimeHealthStatus.FAILED,
            ModelStatus.UNLOADED: RuntimeHealthStatus.STOPPED,
        }
        runtime_status = status_map.get(model_status)
        if runtime_status is None:
            return health

        metadata = dict(health.metadata)
        metadata["model_status"] = _model_status_value(model_status)
        model_resolver = getattr(worker, "_active_tts_model", None)
        try:
            model_type = model_resolver() if callable(model_resolver) else None
        except Exception:
            model_type = None
        normalized_model = str(
            getattr(model_type, "value", model_type) or ""
        ).strip().lower().split(".")[-1]
        if normalized_model:
            metadata["model_type"] = normalized_model
        if is_deferred_tts_model_type(normalized_model):
            metadata.update(deferred_tts_metadata(normalized_model))
            return health.model_copy(
                update={
                    "status": RuntimeHealthStatus.FAILED,
                    "details": OPENVOICE_DEFERRED_DETAILS,
                    "metadata": metadata,
                }
            )
        if (
            runtime_status is RuntimeHealthStatus.READY
            and normalized_model == "openvoice"
        ):
            metadata["voice_ids"] = ["default"]
        else:
            metadata.pop("voice_ids", None)
        return health.model_copy(
            update={"status": runtime_status, "metadata": metadata}
        )

    def _existing_tts_worker(self) -> Any:
        """Return an instantiated worker without triggering its lazy property."""
        worker_manager = getattr(
            self._signal_source, "_worker_manager", None
        )
        if worker_manager is None:
            return None
        try:
            return vars(worker_manager).get("_tts_generator_worker")
        except TypeError:
            return None

    def list_voice_ids(self, model_type: str) -> tuple[str, ...]:
        """Enumerate an explicitly selected eSpeak CLI voice catalog."""
        if is_deferred_tts_model_type(model_type):
            raise EspeakRenderError("tts_backend_unavailable")
        if not self._is_espeak_model_type(model_type):
            raise EspeakRenderError("tts_invalid_request")
        return self._espeak_cli_renderer.catalogue()

    def invoke(self, request: RequestEnvelope) -> ResponseEnvelope:
        """Synthesize with a configured backend or honor explicit playback opt-in."""
        if request.runtime is not RuntimeKind.TTS:
            raise ValueError("LocalFallbackTTSClient only supports TTS")
        if request.action is RuntimeAction.STATUS:
            return self._status_response(request.request_id)
        if request.action is RuntimeAction.LOAD_MODEL:
            return self._load_model(
                request.request_id,
                (request.metadata or {}).get("model_type"),
            )
        if request.action is RuntimeAction.UNLOAD_MODEL:
            return self._unload_model(request.request_id)
        if request.action is not RuntimeAction.INVOKE:
            raise ValueError("LocalFallbackTTSClient only supports invoke")
        invocation = TTSInvocationRequest.model_validate(request.payload)
        configured_model = os.environ.get("AIRUNNER_TTS_MODEL_TYPE")
        requested_model = (invocation.metadata or {}).get("model_type")
        if is_deferred_tts_model_type(
            requested_model or configured_model
        ):
            return self._failure_response(
                request.request_id,
                TTS_BACKEND_UNAVAILABLE_CODE,
                OPENVOICE_DEFERRED_DETAILS,
            )

        if self._is_espeak_model_type(requested_model or configured_model):
            return self._invoke_headless_runtime(
                request.request_id,
                invocation,
                worker=None,
            )

        worker = self._headless_tts_worker()
        active_model = getattr(worker, "_active_tts_model", None)
        try:
            active_model_type = active_model() if callable(active_model) else None
        except Exception:
            active_model_type = None
        if is_deferred_tts_model_type(active_model_type):
            return self._failure_response(
                request.request_id,
                TTS_BACKEND_UNAVAILABLE_CODE,
                OPENVOICE_DEFERRED_DETAILS,
            )
        if worker is not None:
            return self._invoke_headless_runtime(
                request.request_id,
                invocation,
                worker=worker,
            )

        if self._allow_legacy_playback:
            return self._invoke_playback_runtime(request.request_id, invocation)
        return self._failure_response(
            request.request_id,
            TTS_BACKEND_UNAVAILABLE_CODE,
            "No headless TTS backend is configured",
        )

    def _invoke_headless_runtime(
        self,
        request_id: str,
        invocation: TTSInvocationRequest,
        *,
        worker: Any = _UNRESOLVED_WORKER,
    ) -> ResponseEnvelope:
        """Return audio from one headless runtime instead of local playback."""
        if worker is _UNRESOLVED_WORKER:
            worker = self._headless_tts_worker()
        model_type = normalize_tts_model_type(
            self._tts_model_type(invocation, worker)
        )
        unsupported = (
            self._unsupported_headless_openvoice_params(invocation, worker)
            if model_type == "openvoice"
            else []
        )
        if unsupported:
            return self._failure_response(
                request_id,
                "tts_unsupported_parameter",
                "Headless OpenVoice does not support: "
                + ", ".join(unsupported),
            )
        try:
            audio_b64 = self._audio_payload(invocation, worker=worker)
        except EspeakRenderError as exc:
            return self._failure_response(
                request_id,
                exc.code,
                exc.public_message,
                retryable=exc.retryable,
            )
        if audio_b64 is not None:
            return ResponseEnvelope(
                request_id=request_id,
                status=EnvelopeStatus.SUCCEEDED,
                payload={
                    "accepted": True,
                    "audio_b64": audio_b64,
                },
                metadata={"stream": False},
            )
        return self._failure_response(
            request_id,
            "tts_audio_unavailable",
            "Headless TTS runtime could not render audio",
            retryable=True,
        )

    def _invoke_playback_runtime(
        self,
        request_id: str,
        invocation: TTSInvocationRequest,
    ) -> ResponseEnvelope:
        """Queue playback for one local interactive runtime."""
        self._speak(invocation)
        metadata: dict[str, Any] = {"stream": False}
        unsupported = self._unsupported_playback_params(invocation)
        if unsupported:
            metadata["unsupported_params"] = unsupported
            logger.warning(
                "TTS playback ignores caller params for request %s: %s",
                request_id,
                ", ".join(unsupported),
            )
        return ResponseEnvelope(
            request_id=request_id,
            status=EnvelopeStatus.SUCCEEDED,
            payload={"accepted": True},
            metadata=metadata,
        )

    @staticmethod
    def _unsupported_playback_params(
        invocation: TTSInvocationRequest,
    ) -> list[str]:
        """Name caller TTS params the playback path cannot honor."""
        unsupported = []
        if invocation.voice:
            unsupported.append("voice")
        if invocation.speed != 1.0:
            unsupported.append("speed")
        if invocation.model:
            unsupported.append("model")
        return unsupported

    def cancel(self, request_id: str) -> ResponseEnvelope:
        """Interrupt queued or active TTS playback on a best-effort basis."""
        from airunner_common.contract_enums import SignalCode

        logger.warning(
            "TTS playback cancel for request %s is best-effort only",
            request_id,
        )
        self._emit_signal(SignalCode.INTERRUPT_PROCESS_SIGNAL, {})
        return ResponseEnvelope(
            request_id=request_id,
            status=EnvelopeStatus.CANCELLED,
            metadata={"best_effort": True},
        )

    def _load_model(
        self,
        request_id: str,
        requested_model_type: Optional[str] = None,
    ) -> ResponseEnvelope:
        """Enable and load the local TTS model."""
        from airunner_common.contract_enums import ModelStatus, SignalCode

        if is_deferred_tts_model_type(
            requested_model_type or os.environ.get("AIRUNNER_TTS_MODEL_TYPE")
        ):
            return self._failure_response(
                request_id,
                TTS_BACKEND_UNAVAILABLE_CODE,
                OPENVOICE_DEFERRED_DETAILS,
            )

        worker = self._headless_tts_worker()
        if worker is not None:
            active_model = getattr(worker, "_active_tts_model", None)
            try:
                active_model_type = (
                    active_model() if callable(active_model) else None
                )
            except Exception:
                active_model_type = None
            if is_deferred_tts_model_type(active_model_type):
                return self._failure_response(
                    request_id,
                    TTS_BACKEND_UNAVAILABLE_CODE,
                    OPENVOICE_DEFERRED_DETAILS,
                )
            load_tts = getattr(worker, "_load_tts", None)
            current_status = getattr(worker, "_current_tts_status", None)
            if not callable(load_tts) or not callable(current_status):
                return self._failure_response(
                    request_id,
                    "tts_load_failed",
                    "Headless TTS worker is unavailable",
                )

            load_tts()
            status = current_status()
            self._cache_status(status)
            if status in (ModelStatus.LOADED, ModelStatus.READY):
                return ResponseEnvelope(
                    request_id=request_id,
                    status=EnvelopeStatus.SUCCEEDED,
                    payload={"model_status": _model_status_value(status)},
                    metadata=self._status_metadata(),
                )
            if status is ModelStatus.FAILED:
                return self._failure_response(
                    request_id,
                    "tts_load_failed",
                    "TTS load failed",
                )
            return self._failure_response(
                request_id,
                "tts_load_failed",
                "TTS did not reach a loaded state",
                retryable=True,
            )

        return self._wait_for_model_status(
            request_id,
            emit_code=SignalCode.TTS_ENABLE_SIGNAL,
            emit_data={
                "source": "runtime_control",
                "request_scoped": True,
            },
            success_statuses=(ModelStatus.LOADED, ModelStatus.READY),
            timeout_code="tts_load_timeout",
            failure_code="tts_load_failed",
            action_name="TTS load",
        )

    def _unload_model(self, request_id: str) -> ResponseEnvelope:
        """Disable and unload the local TTS model."""
        from airunner_common.contract_enums import ModelStatus, SignalCode

        worker = self._headless_tts_worker()
        if worker is not None:
            unload_tts = getattr(worker, "_unload_tts", None)
            current_status = getattr(worker, "_current_tts_status", None)
            if not callable(unload_tts) or not callable(current_status):
                return self._failure_response(
                    request_id,
                    "tts_unload_failed",
                    "Headless TTS worker is unavailable",
                )

            unload_tts()
            status = current_status()
            self._cache_status(status)
            if status is ModelStatus.UNLOADED:
                return ResponseEnvelope(
                    request_id=request_id,
                    status=EnvelopeStatus.SUCCEEDED,
                    payload={"model_status": _model_status_value(status)},
                    metadata=self._status_metadata(),
                )
            if status is ModelStatus.FAILED:
                return self._failure_response(
                    request_id,
                    "tts_unload_failed",
                    "TTS unload failed",
                )
            return self._failure_response(
                request_id,
                "tts_unload_failed",
                "TTS did not unload cleanly",
                retryable=True,
            )

        return self._wait_for_model_status(
            request_id,
            emit_code=SignalCode.TTS_DISABLE_SIGNAL,
            emit_data={},
            success_statuses=(ModelStatus.UNLOADED,),
            timeout_code="tts_unload_timeout",
            failure_code="tts_unload_failed",
            action_name="TTS unload",
        )

    def _audio_payload(
        self,
        invocation: TTSInvocationRequest,
        *,
        worker: Any = _UNRESOLVED_WORKER,
    ) -> Optional[str]:
        """Return base64 WAV audio when headless synthesis is available."""
        audio_bytes = self._render_audio_bytes(invocation, worker=worker)
        if not audio_bytes:
            return None
        return base64.b64encode(audio_bytes).decode("ascii")

    def _render_audio_bytes(
        self,
        invocation: TTSInvocationRequest,
        *,
        worker: Any = _UNRESOLVED_WORKER,
    ) -> Optional[bytes]:
        """Render one TTS request to WAV bytes in headless mode."""
        if worker is _UNRESOLVED_WORKER:
            selected_model = (
                (invocation.metadata or {}).get("model_type")
                or os.environ.get("AIRUNNER_TTS_MODEL_TYPE")
            )
            worker = (
                None
                if self._is_espeak_model_type(selected_model)
                else self._headless_tts_worker()
            )
        selected_model = normalize_tts_model_type(
            self._tts_model_type(invocation, worker)
            or os.environ.get("AIRUNNER_TTS_MODEL_TYPE")
        )
        if self._is_espeak_model_type(selected_model):
            audio = self._espeak_cli_renderer.render(
                invocation.text,
                voice=invocation.voice,
                speed=invocation.speed,
            )
            self._espeak_cli_ready = True
            return audio
        manager = self._tts_manager(worker)
        request = self._tts_request(invocation, worker)
        if worker is None or manager is None or request is None:
            return None
        audio = manager.generate(request)
        if audio is None:
            return None
        return self._encode_audio(audio, self._sample_rate(manager))

    @staticmethod
    def _is_espeak_model_type(model_type: Any) -> bool:
        """Return whether a model selection names the eSpeak backend."""
        return normalize_tts_model_type(model_type) in {
            "espeak",
            "espeak-ng",
            "espeak_ng",
        }

    def _headless_tts_worker(self):
        """Return the headless TTS worker when one exists."""
        worker_manager = getattr(self._signal_source, "_worker_manager", None)
        if worker_manager is None:
            return None
        return getattr(worker_manager, "tts_generator_worker", None)

    def _tts_manager(self, worker):
        """Return one loaded TTS manager from the headless worker."""
        from airunner_common.contract_enums import ModelStatus

        if worker is None:
            return None
        manager = getattr(worker, "tts", None)
        if manager is None:
            initializer = getattr(worker, "_initialize_tts_model_manager", None)
            if callable(initializer):
                initializer()
            manager = getattr(worker, "tts", None)
        if manager is None:
            return None
        status_getter = getattr(worker, "_current_tts_status", None)
        status = status_getter() if callable(status_getter) else None
        if status not in (ModelStatus.LOADED, ModelStatus.READY):
            loaded = manager.load()
            if loaded is False:
                return None
        return manager

    def _tts_request(self, invocation: TTSInvocationRequest, worker):
        """Return one TTS request only for in-memory audio-capable models."""
        from airunner_services.requests.tts_request import (
            OpenVoiceTTSRequest,
        )
        from airunner_common.contract_enums import TTSModel

        if self._tts_model_type(invocation, worker) != (
            TTSModel.OPENVOICE.value.lower()
        ):
            return None
        chatbot = getattr(worker, "chatbot", None)
        return OpenVoiceTTSRequest(
            message=invocation.text,
            gender=getattr(chatbot, "gender", "Male"),
            speed=round(invocation.speed * 100),
            voice=invocation.voice or "default",
        )

    @staticmethod
    def _unsupported_headless_openvoice_params(
        invocation: TTSInvocationRequest, worker: Any
    ) -> list[str]:
        """Report request parameters OpenVoice cannot apply as requested."""
        unsupported = []
        if invocation.voice not in (None, "default"):
            unsupported.append("voice")
        active_model = LocalFallbackTTSClient._tts_model_type(
            invocation, worker
        )
        if invocation.model and invocation.model not in (active_model,):
            unsupported.append("model")
        return unsupported

    @staticmethod
    def _tts_model_type(invocation: TTSInvocationRequest, worker) -> Optional[str]:
        """Return the active TTS model type as a normalized string."""
        resolver = getattr(worker, "_active_tts_model", None)
        active_model = resolver() if callable(resolver) else None
        if active_model:
            return str(active_model).strip().lower()
        metadata = invocation.metadata or {}
        model_type = metadata.get("model_type")
        if model_type:
            return str(model_type).strip().lower()
        return None

    @staticmethod
    def _sample_rate(manager) -> int:
        """Return the sampling rate for one synthesized audio buffer."""
        converter = getattr(manager, "tone_color_converter", None)
        hps = getattr(converter, "hps", None)
        data = getattr(hps, "data", None)
        return int(getattr(data, "sampling_rate", 24000))

    @staticmethod
    def _encode_audio(audio: Any, sample_rate: int) -> bytes:
        """Encode one waveform as WAV bytes."""
        import soundfile as sf

        buffer = io.BytesIO()
        sf.write(buffer, audio, sample_rate, format="WAV")
        return buffer.getvalue()

    def _speak(self, invocation: TTSInvocationRequest) -> None:
        """Queue a TTS request using the current playback service.

        Voice, speed and model travel in the queued payload for
        consumers that can honor them; the legacy playback path only
        speaks the message text (see _unsupported_playback_params).
        """
        payload = {
            "message": invocation.text,
            "is_end_of_message": True,
            "voice": invocation.voice,
            "speed": invocation.speed,
            "model": invocation.model,
        }
        if hasattr(self._signal_source, "play_audio"):
            self._signal_source.play_audio(invocation.text)
            return
        from airunner_common.contract_enums import SignalCode

        self._emit_signal(SignalCode.TTS_QUEUE_SIGNAL, payload)


class LocalFallbackArtClient(_SignalRuntimeClient):
    """Bridge art runtime requests to the current callback-based pipeline."""

    def __init__(
        self,
        provider: str = DEFAULT_PROVIDER,
        timeout_seconds: Optional[float] = None,
        signal_source: Any = None,
        mediator: Any = None,
        health_provider: Optional[HealthProvider] = None,
    ) -> None:
        resolved_timeout = timeout_seconds
        if resolved_timeout is None:
            resolved_timeout = (
                resolve_art_daemon_runtime_settings().invocation_timeout_seconds
            )
        super().__init__(
            RuntimeKind.ART,
            provider,
            signal_source=signal_source or _build_art_service(),
            mediator=mediator,
            timeout_seconds=resolved_timeout,
            health_provider=health_provider,
            allows_model_control=True,
            model_type=_resolve_model_type("SD"),
        )
        self._art_model_metadata: dict[str, Any] = {}
        self._rmbg_model_manager = None
        self._art_request_lock = threading.Lock()
        self._active_art_request_id: Optional[str] = None
        self._owned_art_request_ids: set[str] = set()
        self._cancelled_art_request_ids: set[str] = set()

    def _status_metadata(self) -> dict[str, Any]:
        """Return cached art metadata for daemon health summaries."""
        metadata = super()._status_metadata()
        metadata.update(self._art_model_metadata)
        return metadata

    def _cache_art_model_metadata(self, image_request) -> None:
        """Store the current art model identity for health summaries."""
        metadata: dict[str, Any] = {}
        if getattr(image_request, "model_path", None):
            metadata["model_path"] = image_request.model_path
        if getattr(image_request, "version", None):
            metadata["model_version"] = image_request.version
        self._art_model_metadata = metadata

    def invoke(self, request: RequestEnvelope) -> ResponseEnvelope:
        """Execute one art request without progress callbacks."""
        return self.invoke_with_progress(request)

    def invoke_with_progress(
        self,
        request: RequestEnvelope,
        progress_callback: Optional[ProgressCallback] = None,
    ) -> ResponseEnvelope:
        """Execute art generation or lightweight control requests."""
        if request.runtime is not RuntimeKind.ART:
            raise ValueError("LocalFallbackArtClient only supports art")
        if request.action is RuntimeAction.STATUS:
            return self._status_response(request.request_id)
        if request.action is RuntimeAction.UNLOAD_MODEL:
            return self._unload_model(request)
        if request.action is RuntimeAction.LOAD_MODEL:
            return self._load_model(request)
        if request.action is not RuntimeAction.INVOKE:
            raise ValueError("LocalFallbackArtClient only supports invoke")
        if self._art_operation(request) == "remove_background":
            return self._remove_background(request)
        return self._generate_image(request, progress_callback)

    def cancel(self, request_id: str) -> ResponseEnvelope:
        """Cancel only the matching art request, never unrelated work."""
        from airunner_common.contract_enums import SignalCode

        with self._art_request_lock:
            if self._active_art_request_id == request_id:
                interrupt_active = True
            elif request_id in self._owned_art_request_ids:
                # The API may cancel after admission but before the runtime
                # invocation thread starts. The invocation consumes this
                # request-owned marker and exits without emitting a signal.
                self._cancelled_art_request_ids.add(request_id)
                interrupt_active = False
            else:
                interrupt_active = False
        if interrupt_active:
            self._emit_signal(
                SignalCode.INTERRUPT_IMAGE_GENERATION_SIGNAL,
                {"request_id": request_id},
            )
        return ResponseEnvelope(
            request_id=request_id,
            status=EnvelopeStatus.CANCELLED,
            metadata={"best_effort": True, "active": interrupt_active},
        )

    def cancel_active(self, request_id: str) -> ResponseEnvelope:
        """Honor an explicit administrator request to interrupt current art."""
        from airunner_common.contract_enums import SignalCode

        self._emit_signal(SignalCode.INTERRUPT_IMAGE_GENERATION_SIGNAL, {})
        return ResponseEnvelope(
            request_id=request_id,
            status=EnvelopeStatus.CANCELLED,
            metadata={"best_effort": True, "administrative": True},
        )

    def finish_request(self, request_id: str) -> None:
        """Forget a completed request's pending cancellation marker."""
        with self._art_request_lock:
            self._owned_art_request_ids.discard(request_id)
            self._cancelled_art_request_ids.discard(request_id)

    def register_request(self, request_id: str) -> None:
        """Register an admitted API request before its runtime call starts."""
        with self._art_request_lock:
            self._owned_art_request_ids.add(request_id)

    def _unload_model(self, request: RequestEnvelope) -> ResponseEnvelope:
        """Unload the current art pipeline or one supported component."""
        from airunner_common.contract_enums import ModelStatus, SignalCode

        component = self._art_component(request)
        if component == "rmbg":
            manager = self._rmbg_model_manager
            if manager is not None:
                manager.unload()
            return ResponseEnvelope(
                request_id=request.request_id,
                status=EnvelopeStatus.SUCCEEDED,
                payload={"accepted": True, "component": component},
            )

        if component == "safety_checker":
            return self._unload_safety_checker_component(request.request_id)

        self._art_model_metadata = {}
        response = self._wait_for_model_status(
            request.request_id,
            emit_code=SignalCode.SD_UNLOAD_SIGNAL,
            emit_data={},
            success_statuses=(ModelStatus.UNLOADED,),
            timeout_code="art_unload_timeout",
            failure_code="art_unload_failed",
            action_name="Art unload",
        )
        if response.status is not EnvelopeStatus.SUCCEEDED:
            return response
        payload = {"accepted": True}
        if response.payload is not None:
            payload.update(response.payload)
        return ResponseEnvelope(
            request_id=request.request_id,
            status=EnvelopeStatus.SUCCEEDED,
            payload=payload,
            metadata=response.metadata,
        )
    
    def _load_model(self, request: RequestEnvelope) -> ResponseEnvelope:
        """Load one explicit art component when supported."""
        component = self._art_component(request)
        if component == "rmbg":
            manager = self._rmbg_manager()
            try:
                manager._load()
            except Exception as exc:
                return self._failure_response(
                    request.request_id,
                    "art_component_load_failed",
                    str(exc),
                )
            return ResponseEnvelope(
                request_id=request.request_id,
                status=EnvelopeStatus.SUCCEEDED,
                payload={"accepted": True, "component": component},
            )

        if component == "safety_checker":
            return self._load_safety_checker_component(request.request_id)

        return self._failure_response(
            request.request_id,
            "art_load_unsupported",
            "Art model loading requires an explicit supported component",
        )

    def _remove_background(self, request: RequestEnvelope) -> ResponseEnvelope:
        """Remove the background from one input image."""
        invocation = ArtInvocationRequest.model_validate(request.payload)
        metadata = invocation.metadata or {}
        image_b64 = metadata.get("image_b64")
        if not image_b64:
            return self._failure_response(
                request.request_id,
                "art_remove_background_missing_image",
                "Background removal requires image_b64 metadata",
            )

        try:
            image_bytes = base64.b64decode(image_b64)
        except Exception as exc:
            return self._failure_response(
                request.request_id,
                "art_remove_background_invalid_image",
                str(exc),
            )

        try:
            with Image.open(io.BytesIO(image_bytes)) as raw_image:
                image = raw_image.copy()
            png_bytes = self._rmbg_manager().remove_background_to_png_bytes(
                image
            )
        except Exception as exc:
            return self._failure_response(
                request.request_id,
                "art_remove_background_failed",
                str(exc),
            )

        return ResponseEnvelope(
            request_id=request.request_id,
            status=EnvelopeStatus.SUCCEEDED,
            payload={
                "images": [base64.b64encode(png_bytes).decode("ascii")],
                "image_count": 1,
            },
        )

    def _generate_image(
        self,
        request: RequestEnvelope,
        progress_callback: Optional[ProgressCallback] = None,
    ) -> ResponseEnvelope:
        """Own one local runtime slot and route cancellation by request id."""
        request_id = request.request_id
        with self._art_request_lock:
            if request_id in self._cancelled_art_request_ids:
                self._cancelled_art_request_ids.discard(request_id)
                return ResponseEnvelope(
                    request_id=request_id,
                    status=EnvelopeStatus.CANCELLED,
                    metadata={"best_effort": True, "active": False},
                )
            if self._active_art_request_id is not None:
                return self._failure_response(
                    request_id,
                    "art_runtime_busy",
                    "Another local art request is active",
                    retryable=True,
                )
            self._active_art_request_id = request_id
        try:
            return self._generate_image_owned(request, progress_callback)
        finally:
            with self._art_request_lock:
                if self._active_art_request_id == request_id:
                    self._active_art_request_id = None

    def _generate_image_owned(
        self,
        request: RequestEnvelope,
        progress_callback: Optional[ProgressCallback] = None,
    ) -> ResponseEnvelope:
        """Generate art through the current callback-based worker flow."""
        from airunner_services.art.managers.stablediffusion.image_request import (
            ImageRequest,
        )
        from airunner_common.contract_enums import SignalCode

        invocation = ArtInvocationRequest.model_validate(request.payload)
        metadata = invocation.metadata
        image_queue: Queue[Any] = Queue()
        pipeline_action = _resolve_art_pipeline_action(metadata)
        generator_section = _resolve_art_generator_section(metadata)

        def on_complete(result: Any) -> None:
            image_queue.put(result)

        if progress_callback is not None:
            progress_callback(
                {
                    "status": "running",
                    "progress": 1.0,
                    "phase": "dispatch",
                }
            )

        image_request = ImageRequest(
            pipeline_action=pipeline_action,
            prompt=invocation.prompt,
            negative_prompt=invocation.negative_prompt,
            model_path=invocation.model or "",
            skip_auto_export=bool(
                metadata.get("skip_auto_export", False)
            ),
            scheduler=_resolve_art_request_scheduler(metadata),
            version=_resolve_art_request_version(metadata),
            steps=invocation.steps,
            scale=invocation.cfg_scale,
            seed=invocation.seed or 42,
            random_seed=invocation.seed is None,
            n_samples=invocation.num_images,
            images_per_batch=invocation.num_images,
            strength=_resolve_art_request_strength(metadata),
            width=invocation.width,
            height=invocation.height,
            callback=on_complete,
            image=_resolve_art_request_image(metadata),
            mask=_resolve_art_request_mask(metadata),
            generator_section=generator_section,
            outpaint_mask_blur=_resolve_art_request_outpaint_mask_blur(
                metadata,
            ),
        )
        self._cache_art_model_metadata(image_request)
        signal_payload = {
            "image_request": image_request,
            "request_id": request.request_id,
        }
        active_rect = _resolve_art_active_rect(metadata)
        if active_rect is not None:
            signal_payload["active_rect"] = active_rect

        # Ensure the SD worker is created and registered for signals
        # before we emit DO_GENERATE_SIGNAL.  The worker is lazily
        # instantiated by ServiceWorkerManager; accessing it here
        # triggers creation and signal-handler registration so the
        # signal below is received.
        logger.info(
            "[LocalFallbackArtClient] Creating SD worker and emitting "
            f"DO_GENERATE_SIGNAL model={image_request.model_path!r} "
            f"version={image_request.version!r}"
        )
        sd_worker = self._headless_art_worker(create=True)
        if sd_worker is None:
            logger.error(
                "[LocalFallbackArtClient] ERROR: SD worker could not "
                "be created (worker_manager not found on signal_source)"
            )
            return self._failure_response(
                request.request_id,
                "art_worker_unavailable",
                "Local art worker is unavailable",
                retryable=True,
            )
        else:
            logger.info(
                "[LocalFallbackArtClient] SD worker created: "
                f"type={type(sd_worker).__name__}"
            )

        progress_handler = None
        if progress_callback is not None:
            progress_handler = self._build_art_progress_handler(progress_callback)
            self._mediator.register(
                SignalCode.SD_PROGRESS_SIGNAL,
                progress_handler,
            )
        timed_out = False
        try:
            self._emit_signal(
                SignalCode.DO_GENERATE_SIGNAL,
                signal_payload,
            )
            try:
                result = image_queue.get(timeout=self._timeout_seconds)
            except Empty:
                # A queue timeout is not proof that the worker stopped. Send
                # request-owned cancellation and keep this invocation (and its
                # admission reservation) alive until the worker acknowledges
                # the queued or active request through its callback.
                timed_out = True
                self.cancel(request.request_id)
                result = image_queue.get()
        finally:
            if progress_handler is not None:
                self._mediator.unregister(
                    SignalCode.SD_PROGRESS_SIGNAL,
                    progress_handler,
                )
        if timed_out:
            return self._failure_response(
                request.request_id,
                "art_timeout",
                "Timed out waiting for art response",
                retryable=True,
            )
        if isinstance(result, str):
            return self._failure_response(
                request.request_id,
                "art_generation_failed",
                result,
            )
        return ResponseEnvelope(
            request_id=request.request_id,
            status=EnvelopeStatus.SUCCEEDED,
            payload=self._art_payload(result),
        )

    @staticmethod
    def _build_art_progress_handler(
        progress_callback: ProgressCallback,
    ) -> Callable[[dict[str, Any]], None]:
        """Return a progress handler that normalizes SD progress events."""

        def on_progress(data: dict[str, Any]) -> None:
            step = int(data.get("step") or 0)
            total = int(data.get("total") or 0)
            progress = 0.0
            if total > 0:
                progress = min(100.0, max(0.0, (step / total) * 100.0))
            progress_callback(
                {
                    "status": "running",
                    "progress": progress,
                    "step": step,
                    "total": total,
                }
            )

        return on_progress

    @staticmethod
    def _art_payload(result: Any) -> dict[str, Any]:
        """Convert the current art response into a neutral payload."""
        images = []
        for image in getattr(result, "images", []) or []:
            images.append(LocalFallbackArtClient._encode_image(image))
        return {
            "images": images,
            "image_count": len(images),
            "node_id": getattr(result, "node_id", None),
        }

    @staticmethod
    def _encode_image(image: Any) -> str:
        """Encode a PIL image as a base64 PNG string."""
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        return base64.b64encode(buffer.getvalue()).decode("ascii")

    @staticmethod
    def _art_component(request: RequestEnvelope) -> str:
        """Return the requested art component name."""
        component = str(request.metadata.get("component") or "").strip()
        return component.lower()

    @staticmethod
    def _art_operation(request: RequestEnvelope) -> str:
        """Return the requested art operation name."""
        return _resolve_art_operation(request.metadata)

    def _rmbg_manager(self):
        """Return one lazy RMBG model manager."""
        if self._rmbg_model_manager is None:
            from airunner_services.art.managers.rmbg import RMBGModelManager

            self._rmbg_model_manager = RMBGModelManager()
        return self._rmbg_model_manager

    def _headless_art_worker(self, *, create: bool = False):
        """Return the headless art worker when one exists."""
        worker_manager = getattr(self._signal_source, "_worker_manager", None)
        if worker_manager is None:
            return None
        if create:
            return getattr(worker_manager, "sd_worker", None)
        return getattr(worker_manager, "_sd_worker", None)

    def _art_model_manager(self, *, create: bool = False):
        """Return the headless SD model manager when one exists."""
        worker = self._headless_art_worker(create=create)
        if worker is None:
            return None
        return getattr(worker, "model_manager", None)

    def _load_safety_checker_component(
        self,
        request_id: str,
    ) -> ResponseEnvelope:
        """Load the SD safety checker through the service manager."""
        manager = self._art_model_manager(create=True)
        if manager is None:
            return self._failure_response(
                request_id,
                "art_component_unavailable",
                "Art worker is not available for safety checker loading",
            )

        loader = getattr(manager, "_load_safety_checker", None)
        if not callable(loader):
            return self._failure_response(
                request_id,
                "art_component_unavailable",
                "Safety checker loading is unavailable",
            )

        try:
            loaded = bool(loader())
        except Exception as exc:
            return self._failure_response(
                request_id,
                "art_component_load_failed",
                str(exc),
            )
        if not loaded:
            return self._failure_response(
                request_id,
                "art_component_load_failed",
                "Safety checker could not be loaded",
            )

        return ResponseEnvelope(
            request_id=request_id,
            status=EnvelopeStatus.SUCCEEDED,
            payload={"accepted": True, "component": "safety_checker"},
        )

    def _unload_safety_checker_component(
        self,
        request_id: str,
    ) -> ResponseEnvelope:
        """Unload the SD safety checker through the service manager."""
        manager = self._art_model_manager(create=False)
        if manager is not None:
            unload = getattr(manager, "_unload_safety_checker", None)
            if callable(unload):
                unload()
        return ResponseEnvelope(
            request_id=request_id,
            status=EnvelopeStatus.SUCCEEDED,
            payload={"accepted": True, "component": "safety_checker"},
        )


def register_local_fallback_clients(
    registry: RuntimeRegistry,
    llm_client: Optional[RuntimeClient] = None,
    stt_client: Optional[RuntimeClient] = None,
    tts_client: Optional[RuntimeClient] = None,
    art_client: Optional[RuntimeClient] = None,
    *,
    include_llm: bool = True,
) -> RuntimeRegistry:
    """Register the current local fallback clients in a runtime registry."""
    clients = []
    if include_llm:
        clients.append(llm_client or LocalFallbackLLMClient())
    clients.extend(
        [
            stt_client or LocalFallbackSTTClient(),
            tts_client or LocalFallbackTTSClient(),
            art_client or LocalFallbackArtClient(),
        ]
    )
    for client in clients:
        for route in _local_fallback_routes(
            client.descriptor.runtime,
            client.descriptor.provider,
        ):
            registry.register(route, client)
    return registry


def _local_fallback_routes(
    runtime: RuntimeKind, provider: str
) -> tuple[RuntimeRoute, RuntimeRoute]:
    """Return default and explicit local fallback route aliases."""
    return (
        RuntimeRoute(runtime, provider=provider),
        RuntimeRoute(
            runtime,
            provider=provider,
            deployment_mode=RuntimeMode.LOCAL_FALLBACK.value,
        ),
    )
