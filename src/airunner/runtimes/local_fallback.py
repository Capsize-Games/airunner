"""Local fallback runtime clients backed by existing signal services."""

from __future__ import annotations

import base64
import io
from queue import Empty, Queue
from typing import Any, Callable, Iterable, Optional

from airunner.ipc.messages import (
    EnvelopeStatus,
    ErrorEnvelope,
    RequestEnvelope,
    ResponseEnvelope,
    StreamDelta,
)
from airunner.runtimes.base import RuntimeClient
from airunner.runtimes.contracts import (
    ArtInvocationRequest,
    LLMInvocationRequest,
    RuntimeAction,
    RuntimeDescriptor,
    RuntimeHealth,
    RuntimeHealthStatus,
    RuntimeKind,
    RuntimeMode,
    STTInvocationRequest,
    TTSInvocationRequest,
    TransportKind,
)
from airunner.runtimes.registry import RuntimeRegistry, RuntimeRoute

DEFAULT_PROVIDER = "local"
DEFAULT_TIMEOUT_SECONDS = 120.0

LLMRequestFactory = Callable[[LLMInvocationRequest], Any]
HealthProvider = Callable[[], RuntimeHealthStatus]


def _build_signal_mediator() -> Any:
    """Create the default signal mediator lazily."""
    from airunner.utils.application.signal_mediator import SignalMediator

    return SignalMediator()


def _build_llm_service() -> Any:
    """Create the default LLM API service lazily."""
    from airunner.components.llm.api.llm_services import LLMAPIService

    return LLMAPIService()


def _build_stt_service() -> Any:
    """Create the default STT API service lazily."""
    from airunner.components.stt.api.stt_services import STTAPIService

    return STTAPIService()


def _build_tts_service() -> Any:
    """Create the default TTS API service lazily."""
    from airunner.components.tts.api.tts_services import TTSAPIService

    return TTSAPIService()


def _build_art_service() -> Any:
    """Create the default art API service lazily."""
    from airunner.components.art.api.art_services import ARTAPIService

    return ARTAPIService()


def _build_llm_request(invocation: LLMInvocationRequest) -> Any:
    """Create an LLM request object for the legacy signal path."""
    from airunner.components.llm.managers.llm_request import LLMRequest

    request = LLMRequest()
    request.temperature = invocation.temperature
    if invocation.max_tokens is not None:
        request.max_new_tokens = invocation.max_tokens
    if invocation.model:
        request.model = invocation.model
    return request


def _resolve_model_type(name: str) -> Any:
    """Resolve a model type lazily to avoid eager imports."""
    from airunner.enums import ModelType

    return getattr(ModelType, name)


def _model_health_status(model_status: Any) -> RuntimeHealthStatus:
    """Translate application model status into runtime health status."""
    from airunner.enums import ModelStatus

    status_map = {
        None: RuntimeHealthStatus.UNKNOWN,
        ModelStatus.LOADING: RuntimeHealthStatus.STARTING,
        ModelStatus.LOADED: RuntimeHealthStatus.READY,
        ModelStatus.READY: RuntimeHealthStatus.READY,
        ModelStatus.FAILED: RuntimeHealthStatus.FAILED,
        ModelStatus.UNLOADED: RuntimeHealthStatus.STOPPED,
    }
    return status_map.get(model_status, RuntimeHealthStatus.UNKNOWN)


def _model_status_value(model_status: Any) -> str:
    """Return a stable string representation of a model status."""
    return getattr(model_status, "value", "")


class _SignalRuntimeClient(RuntimeClient):
    """Common helpers for signal-backed local fallback clients."""

    def __init__(
        self,
        runtime: RuntimeKind,
        provider: str,
        *,
        signal_source: Any = None,
        mediator: Any = None,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        health_provider: Optional[HealthProvider] = None,
        supports_streaming: bool = False,
        allows_model_control: bool = True,
        model_type: Any = None,
    ) -> None:
        self.descriptor = RuntimeDescriptor(
            runtime=runtime,
            provider=provider,
            mode=RuntimeMode.LOCAL_FALLBACK,
            transport=TransportKind.IN_PROCESS,
            supports_streaming=supports_streaming,
            allows_model_control=allows_model_control,
        )
        self._signal_source = signal_source or _build_signal_mediator()
        self._mediator = mediator or _build_signal_mediator()
        self._timeout_seconds = timeout_seconds
        self._health_provider = health_provider
        self._last_model_status = None
        self._model_type = model_type

    def healthcheck(self) -> RuntimeHealth:
        """Return current health state for the runtime client."""
        if self._health_provider is not None:
            return RuntimeHealth(
                descriptor=self.descriptor,
                status=self._health_provider(),
            )
        return RuntimeHealth(
            descriptor=self.descriptor,
            status=_model_health_status(self._last_model_status),
            details=_model_status_value(self._last_model_status),
            metadata=self._status_metadata(),
        )

    def _emit_signal(self, code: Any, data: Optional[dict[str, Any]] = None):
        """Emit a signal through the configured source."""
        emitter = getattr(self._signal_source, "emit_signal", None)
        if emitter is not None:
            emitter(code, data or {})
            return
        self._mediator.emit_signal(code, data or {})

    def _status_response(self, request_id: str) -> ResponseEnvelope:
        """Return a response envelope for the current client status."""
        health = self.healthcheck()
        return ResponseEnvelope(
            request_id=request_id,
            status=EnvelopeStatus.SUCCEEDED,
            payload={"status": health.status.value},
            metadata=health.metadata,
        )

    def _status_metadata(self) -> dict[str, Any]:
        """Return cached model metadata when available."""
        if self._last_model_status is None:
            return {}
        return {"model_status": _model_status_value(self._last_model_status)}

    def _cache_status(self, model_status: Any) -> None:
        """Track the most recent model status for health checks."""
        self._last_model_status = model_status

    def _matches_model(self, model: Any) -> bool:
        """Return True when a status event targets this client's model."""
        if self._model_type is None:
            return True
        expected = getattr(self._model_type, "value", self._model_type)
        actual = getattr(model, "value", model)
        return actual == expected

    def _wait_for_model_status(
        self,
        request_id: str,
        *,
        emit_code: Any,
        emit_data: Optional[dict[str, Any]],
        success_statuses: tuple[Any, ...],
        timeout_code: str,
        failure_code: str,
        action_name: str,
    ) -> ResponseEnvelope:
        """Emit a control signal and wait for the matching model status."""
        from airunner.enums import ModelStatus, SignalCode

        status_queue: Queue[Any] = Queue()

        def on_status_changed(data: dict[str, Any]) -> None:
            model = data.get("model")
            if not self._matches_model(model):
                return
            status = data.get("status")
            self._cache_status(status)
            if status in success_statuses or status is ModelStatus.FAILED:
                status_queue.put(status)

        self._mediator.register(
            SignalCode.MODEL_STATUS_CHANGED_SIGNAL,
            on_status_changed,
        )
        try:
            self._emit_signal(emit_code, emit_data)
            try:
                status = status_queue.get(timeout=self._timeout_seconds)
            except Empty:
                return self._failure_response(
                    request_id,
                    timeout_code,
                    f"{action_name} timed out",
                    retryable=True,
                )
        finally:
            self._mediator.unregister(
                SignalCode.MODEL_STATUS_CHANGED_SIGNAL,
                on_status_changed,
            )

        if status is ModelStatus.FAILED:
            return self._failure_response(
                request_id,
                failure_code,
                f"{action_name} failed",
            )
        return ResponseEnvelope(
            request_id=request_id,
            status=EnvelopeStatus.SUCCEEDED,
            payload={"model_status": _model_status_value(status)},
            metadata=self._status_metadata(),
        )

    @staticmethod
    def _failure_response(
        request_id: str,
        code: str,
        message: str,
        *,
        retryable: bool = False,
    ) -> ResponseEnvelope:
        """Create a failure response envelope."""
        return ResponseEnvelope(
            request_id=request_id,
            status=EnvelopeStatus.FAILED,
            error=ErrorEnvelope(
                code=code,
                message=message,
                retryable=retryable,
            ),
        )


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
    ) -> None:
        llm_service = llm_service or _build_llm_service()
        super().__init__(
            RuntimeKind.LLM,
            provider,
            signal_source=llm_service,
            mediator=mediator,
            timeout_seconds=timeout_seconds,
            health_provider=health_provider,
            supports_streaming=True,
            allows_model_control=True,
            model_type=_resolve_model_type("LLM"),
        )
        self._llm_service = llm_service
        self._llm_request_factory = llm_request_factory or _build_llm_request

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
        from airunner.enums import ModelStatus, SignalCode

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
        from airunner.enums import ModelStatus, SignalCode

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
        from airunner.enums import LLMActionType

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


class LocalFallbackSTTClient(_SignalRuntimeClient):
    """Bridge STT runtime requests to the current synchronous signal path."""

    def __init__(
        self,
        provider: str = DEFAULT_PROVIDER,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        signal_source: Any = None,
        mediator: Any = None,
        health_provider: Optional[HealthProvider] = None,
    ) -> None:
        super().__init__(
            RuntimeKind.STT,
            provider,
            signal_source=signal_source or _build_stt_service(),
            mediator=mediator,
            timeout_seconds=timeout_seconds,
            health_provider=health_provider,
            model_type=_resolve_model_type("STT"),
        )

    def invoke(self, request: RequestEnvelope) -> ResponseEnvelope:
        """Execute STT invocation or model-control requests."""
        if request.runtime is not RuntimeKind.STT:
            raise ValueError("LocalFallbackSTTClient only supports STT")
        if request.action is RuntimeAction.STATUS:
            return self._status_response(request.request_id)
        if request.action is RuntimeAction.LOAD_MODEL:
            return self._load_model(request.request_id)
        if request.action is RuntimeAction.UNLOAD_MODEL:
            return self._unload_model(request.request_id)
        if request.action is not RuntimeAction.INVOKE:
            raise ValueError("LocalFallbackSTTClient only supports invoke")
        return self._transcribe(request)

    def cancel(self, request_id: str) -> ResponseEnvelope:
        """Interrupt an STT request on a best-effort basis."""
        from airunner.enums import SignalCode

        self._emit_signal(SignalCode.INTERRUPT_PROCESS_SIGNAL, {})
        return ResponseEnvelope(
            request_id=request_id,
            status=EnvelopeStatus.CANCELLED,
            metadata={"best_effort": True},
        )

    def _load_model(self, request_id: str) -> ResponseEnvelope:
        """Load the local STT model."""
        from airunner.enums import ModelStatus, SignalCode

        return self._wait_for_model_status(
            request_id,
            emit_code=SignalCode.STT_LOAD_SIGNAL,
            emit_data={},
            success_statuses=(ModelStatus.LOADED, ModelStatus.READY),
            timeout_code="stt_load_timeout",
            failure_code="stt_load_failed",
            action_name="STT load",
        )

    def _unload_model(self, request_id: str) -> ResponseEnvelope:
        """Unload the local STT model."""
        from airunner.enums import ModelStatus, SignalCode

        return self._wait_for_model_status(
            request_id,
            emit_code=SignalCode.STT_UNLOAD_SIGNAL,
            emit_data={},
            success_statuses=(ModelStatus.UNLOADED,),
            timeout_code="stt_unload_timeout",
            failure_code="stt_unload_failed",
            action_name="STT unload",
        )

    def _transcribe(self, request: RequestEnvelope) -> ResponseEnvelope:
        """Run a transcription request through the working response signal."""
        from airunner.enums import SignalCode

        invocation = STTInvocationRequest.model_validate(request.payload)
        try:
            audio_bytes = base64.b64decode(invocation.audio_b64, validate=True)
        except Exception:
            return self._failure_response(
                request.request_id,
                "stt_invalid_audio",
                "Invalid base64 audio payload",
            )

        transcription_queue: Queue[Any] = Queue()

        def on_transcription(data: dict[str, Any]) -> None:
            transcription = data.get("transcription")
            if transcription is not None:
                transcription_queue.put(transcription)

        self._mediator.register(
            SignalCode.AUDIO_PROCESSOR_RESPONSE_SIGNAL,
            on_transcription,
        )
        try:
            self._emit_signal(
                SignalCode.AUDIO_CAPTURE_WORKER_RESPONSE_SIGNAL,
                {"item": audio_bytes},
            )
            try:
                transcription = transcription_queue.get(
                    timeout=self._timeout_seconds
                )
            except Empty:
                return self._failure_response(
                    request.request_id,
                    "stt_timeout",
                    "Timed out waiting for STT response",
                    retryable=True,
                )
        finally:
            self._mediator.unregister(
                SignalCode.AUDIO_PROCESSOR_RESPONSE_SIGNAL,
                on_transcription,
            )

        payload = self._transcription_payload(transcription, invocation.language)
        return ResponseEnvelope(
            request_id=request.request_id,
            status=EnvelopeStatus.SUCCEEDED,
            payload=payload,
        )

    @staticmethod
    def _transcription_payload(
        transcription: Any,
        language: Optional[str],
    ) -> dict[str, Any]:
        """Normalize the current STT response payload shape."""
        if isinstance(transcription, dict):
            return {
                "text": transcription.get("text")
                or transcription.get("transcription", ""),
                "language": transcription.get("language") or language,
            }
        return {"text": str(transcription), "language": language}


class LocalFallbackTTSClient(_SignalRuntimeClient):
    """Bridge TTS runtime requests to the existing playback-oriented path."""

    def __init__(
        self,
        provider: str = DEFAULT_PROVIDER,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        signal_source: Any = None,
        mediator: Any = None,
        health_provider: Optional[HealthProvider] = None,
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

    def invoke(self, request: RequestEnvelope) -> ResponseEnvelope:
        """Queue playback or execute TTS model-control actions."""
        if request.runtime is not RuntimeKind.TTS:
            raise ValueError("LocalFallbackTTSClient only supports TTS")
        if request.action is RuntimeAction.STATUS:
            return self._status_response(request.request_id)
        if request.action is RuntimeAction.LOAD_MODEL:
            return self._load_model(request.request_id)
        if request.action is RuntimeAction.UNLOAD_MODEL:
            return self._unload_model(request.request_id)
        if request.action is not RuntimeAction.INVOKE:
            raise ValueError("LocalFallbackTTSClient only supports invoke")
        invocation = TTSInvocationRequest.model_validate(request.payload)
        self._speak(invocation.text)
        return ResponseEnvelope(
            request_id=request.request_id,
            status=EnvelopeStatus.SUCCEEDED,
            payload={"accepted": True},
            metadata={"stream": False},
        )

    def cancel(self, request_id: str) -> ResponseEnvelope:
        """Interrupt queued or active TTS playback on a best-effort basis."""
        from airunner.enums import SignalCode

        self._emit_signal(SignalCode.INTERRUPT_PROCESS_SIGNAL, {})
        return ResponseEnvelope(
            request_id=request_id,
            status=EnvelopeStatus.CANCELLED,
            metadata={"best_effort": True},
        )

    def _load_model(self, request_id: str) -> ResponseEnvelope:
        """Enable and load the local TTS model."""
        from airunner.enums import ModelStatus, SignalCode

        return self._wait_for_model_status(
            request_id,
            emit_code=SignalCode.TTS_ENABLE_SIGNAL,
            emit_data={},
            success_statuses=(ModelStatus.LOADED, ModelStatus.READY),
            timeout_code="tts_load_timeout",
            failure_code="tts_load_failed",
            action_name="TTS load",
        )

    def _unload_model(self, request_id: str) -> ResponseEnvelope:
        """Disable and unload the local TTS model."""
        from airunner.enums import ModelStatus, SignalCode

        return self._wait_for_model_status(
            request_id,
            emit_code=SignalCode.TTS_DISABLE_SIGNAL,
            emit_data={},
            success_statuses=(ModelStatus.UNLOADED,),
            timeout_code="tts_unload_timeout",
            failure_code="tts_unload_failed",
            action_name="TTS unload",
        )

    def _speak(self, text: str) -> None:
        """Queue a TTS request using the current playback service."""
        if hasattr(self._signal_source, "play_audio"):
            self._signal_source.play_audio(text)
            return
        from airunner.enums import SignalCode

        self._emit_signal(
            SignalCode.TTS_QUEUE_SIGNAL,
            {"message": text, "is_end_of_message": True},
        )


class LocalFallbackArtClient(_SignalRuntimeClient):
    """Bridge art runtime requests to the current callback-based pipeline."""

    def __init__(
        self,
        provider: str = DEFAULT_PROVIDER,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        signal_source: Any = None,
        mediator: Any = None,
        health_provider: Optional[HealthProvider] = None,
    ) -> None:
        super().__init__(
            RuntimeKind.ART,
            provider,
            signal_source=signal_source or _build_art_service(),
            mediator=mediator,
            timeout_seconds=timeout_seconds,
            health_provider=health_provider,
            allows_model_control=False,
        )

    def invoke(self, request: RequestEnvelope) -> ResponseEnvelope:
        """Execute art generation or lightweight control requests."""
        if request.runtime is not RuntimeKind.ART:
            raise ValueError("LocalFallbackArtClient only supports art")
        if request.action is RuntimeAction.STATUS:
            return self._status_response(request.request_id)
        if request.action is RuntimeAction.UNLOAD_MODEL:
            return self._unload_model(request.request_id)
        if request.action is RuntimeAction.LOAD_MODEL:
            return self._failure_response(
                request.request_id,
                "art_load_unsupported",
                "Art model loading is driven by generation requests",
            )
        if request.action is not RuntimeAction.INVOKE:
            raise ValueError("LocalFallbackArtClient only supports invoke")
        return self._generate_image(request)

    def cancel(self, request_id: str) -> ResponseEnvelope:
        """Interrupt active art generation on a best-effort basis."""
        from airunner.enums import SignalCode

        self._emit_signal(SignalCode.INTERRUPT_IMAGE_GENERATION_SIGNAL, {})
        return ResponseEnvelope(
            request_id=request_id,
            status=EnvelopeStatus.CANCELLED,
            metadata={"best_effort": True},
        )

    def _unload_model(self, request_id: str) -> ResponseEnvelope:
        """Unload the current art pipeline on a best-effort basis."""
        from airunner.enums import SignalCode

        self._emit_signal(SignalCode.SD_UNLOAD_SIGNAL, {})
        return ResponseEnvelope(
            request_id=request_id,
            status=EnvelopeStatus.SUCCEEDED,
            payload={"accepted": True},
        )

    def _generate_image(self, request: RequestEnvelope) -> ResponseEnvelope:
        """Generate art through the current callback-based worker flow."""
        from airunner.components.art.managers.stablediffusion.image_request import (
            ImageRequest,
        )
        from airunner.enums import GeneratorSection, SignalCode

        invocation = ArtInvocationRequest.model_validate(request.payload)
        image_queue: Queue[Any] = Queue()

        def on_complete(result: Any) -> None:
            image_queue.put(result)

        image_request = ImageRequest(
            prompt=invocation.prompt,
            negative_prompt=invocation.negative_prompt,
            model_path=invocation.model or "",
            steps=invocation.steps,
            scale=invocation.cfg_scale,
            seed=invocation.seed or 42,
            random_seed=invocation.seed is None,
            n_samples=invocation.num_images,
            images_per_batch=invocation.num_images,
            width=invocation.width,
            height=invocation.height,
            callback=on_complete,
            generator_section=GeneratorSection.TXT2IMG,
        )
        if invocation.model:
            self._emit_art_model_selection(invocation)

        self._emit_signal(
            SignalCode.DO_GENERATE_SIGNAL,
            {"image_request": image_request},
        )
        try:
            result = image_queue.get(timeout=self._timeout_seconds)
        except Empty:
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

    def _emit_art_model_selection(
        self, invocation: ArtInvocationRequest
    ) -> None:
        """Emit optional art model metadata before generation."""
        from airunner.enums import SignalCode

        metadata = invocation.metadata
        self._emit_signal(
            SignalCode.SD_ART_MODEL_CHANGED,
            {
                "model": invocation.model,
                "version": metadata.get("version"),
                "pipeline": metadata.get("pipeline"),
            },
        )

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


def register_local_fallback_clients(
    registry: RuntimeRegistry,
    llm_client: Optional[RuntimeClient] = None,
    stt_client: Optional[RuntimeClient] = None,
    tts_client: Optional[RuntimeClient] = None,
    art_client: Optional[RuntimeClient] = None,
) -> RuntimeRegistry:
    """Register the current local fallback clients in a runtime registry."""
    clients = (
        llm_client or LocalFallbackLLMClient(),
        stt_client or LocalFallbackSTTClient(),
        tts_client or LocalFallbackTTSClient(),
        art_client or LocalFallbackArtClient(),
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