"""In-process art executor for the art sidecar daemon.

This module replaces LocalFallbackArtClient for the art sidecar subprocess.
When AIRUNNER_ART_SIDECAR_PROCESS=1, the sidecar daemon handles art requests
via this executor instead of routing through the signal-based API services.

The executor bridges the runtime contract (ArtInvocationRequest) to the
in-process SD pipeline without depending on the legacy signal mediator.
"""

from __future__ import annotations

import base64
import io
from queue import Empty, Queue
from typing import Any, Callable, Optional

from airunner.ipc.messages import (
    EnvelopeStatus,
    ErrorEnvelope,
    RequestEnvelope,
    ResponseEnvelope,
)
from airunner.runtimes.base import RuntimeClient
from airunner.runtimes.contracts import (
    ArtInvocationRequest,
    RuntimeAction,
    RuntimeDescriptor,
    RuntimeHealth,
    RuntimeHealthStatus,
    RuntimeKind,
    RuntimeMode,
    TransportKind,
)
from airunner.runtimes.art_daemon_runtime_settings import (
    resolve_art_daemon_runtime_settings,
)
from airunner.runtimes.registry import RuntimeRegistry, RuntimeRoute

DEFAULT_PROVIDER = "local"
DEFAULT_TIMEOUT_SECONDS = 120.0
ProgressCallback = Callable[[dict[str, Any]], None]
HealthProvider = Callable[[], RuntimeHealthStatus]


def _build_signal_mediator() -> Any:
    """Create the default signal mediator lazily."""
    from airunner.utils.application.signal_mediator import SignalMediator

    return SignalMediator()


def _resolve_art_request_version(metadata: dict[str, Any]) -> str:
    """Return the model version carried by one art invocation."""
    from airunner.enums import normalize_art_version

    version = str(metadata.get("version") or "").strip()
    if version:
        return normalize_art_version(version)
    from airunner.enums import DEFAULT_ART_VERSION

    return DEFAULT_ART_VERSION.value


def _resolve_art_request_scheduler(metadata: dict[str, Any]) -> str:
    """Return the scheduler carried by one art invocation."""
    scheduler = str(metadata.get("scheduler") or "").strip()
    if scheduler:
        return scheduler
    from airunner.settings import AIRUNNER_DEFAULT_SCHEDULER

    return AIRUNNER_DEFAULT_SCHEDULER


def _resolve_art_pipeline_action(metadata: dict[str, Any]) -> str:
    """Return the requested art pipeline action."""
    pipeline_action = str(metadata.get("pipeline") or "").strip()
    if pipeline_action:
        return pipeline_action
    return "txt2img"


def _resolve_art_generator_section(metadata: dict[str, Any]) -> Any:
    """Return the requested generator section for one art job."""
    from airunner.enums import GeneratorSection

    pipeline_action = _resolve_art_pipeline_action(metadata)
    try:
        return GeneratorSection(pipeline_action)
    except ValueError:
        return GeneratorSection.TXT2IMG


def _resolve_art_request_strength(metadata: dict[str, Any]) -> float:
    """Return one normalized strength value for image-conditioned jobs."""
    try:
        return float(metadata.get("strength"))
    except (TypeError, ValueError):
        return 0.5


def _resolve_art_request_image(metadata: dict[str, Any]) -> Any:
    """Return one decoded PIL image carried by the art invocation."""
    image_b64 = metadata.get("image_b64")
    if not image_b64:
        return None
    try:
        from PIL import Image

        image_bytes = base64.b64decode(image_b64)
        with Image.open(io.BytesIO(image_bytes)) as image:
            return image.convert("RGB")
    except Exception:
        return None


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


class SidecarArtExecutor(_SignalRuntimeClient):
    """Execute art generation in-process for the art sidecar daemon.

    Receives ArtInvocationRequest envelopes and dispatches them directly
    to the SD pipeline via the existing signal infrastructure. This
    replaces LocalFallbackArtClient for sidecar subprocesses.
    """

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
        signal_source = signal_source or self._build_art_service()
        super().__init__(
            RuntimeKind.ART,
            provider,
            signal_source=signal_source,
            mediator=mediator,
            timeout_seconds=resolved_timeout,
            health_provider=health_provider,
            allows_model_control=False,
        )
        self._art_model_metadata: dict[str, Any] = {}

    @staticmethod
    def _build_art_service() -> Any:
        """Create the default art API service lazily."""
        from airunner.components.art.api.art_services import ARTAPIService

        return ARTAPIService()

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
            raise ValueError("SidecarArtExecutor only supports art")
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
            raise ValueError("SidecarArtExecutor only supports invoke")
        return self._generate_image(request, progress_callback)

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

        self._art_model_metadata = {}
        self._emit_signal(SignalCode.SD_UNLOAD_SIGNAL, {})
        return ResponseEnvelope(
            request_id=request_id,
            status=EnvelopeStatus.SUCCEEDED,
            payload={"accepted": True},
        )

    def _generate_image(
        self,
        request: RequestEnvelope,
        progress_callback: Optional[ProgressCallback] = None,
    ) -> ResponseEnvelope:
        """Generate art through the current callback-based worker flow."""
        from airunner.components.art.managers.stablediffusion.image_request import (
            ImageRequest,
        )
        from airunner.enums import SignalCode

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
            generator_section=generator_section,
        )
        self._cache_art_model_metadata(image_request)

        progress_handler = None
        if progress_callback is not None:
            progress_handler = self._build_art_progress_handler(progress_callback)
            self._mediator.register(
                SignalCode.SD_PROGRESS_SIGNAL,
                progress_handler,
            )
        try:
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
        finally:
            if progress_handler is not None:
                self._mediator.unregister(
                    SignalCode.SD_PROGRESS_SIGNAL,
                    progress_handler,
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
            images.append(SidecarArtExecutor._encode_image(image))
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


def register_sidecar_art_executor(
    registry: RuntimeRegistry,
    art_client: Optional[RuntimeClient] = None,
) -> RuntimeRegistry:
    """Register the in-process art executor under the local fallback route."""
    client = art_client or SidecarArtExecutor()
    routes = (
        RuntimeRoute(RuntimeKind.ART, provider=DEFAULT_PROVIDER),
        RuntimeRoute(
            RuntimeKind.ART,
            provider=DEFAULT_PROVIDER,
            deployment_mode=RuntimeMode.LOCAL_FALLBACK.value,
        ),
    )
    for route in routes:
        registry.register(route, client)
    return registry
