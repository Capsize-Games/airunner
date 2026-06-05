"""Local fallback art runtime client."""
from __future__ import annotations

import base64
import io
from queue import Queue
from typing import Any, Callable, Optional

from airunner_services.ipc.messages import (
    EnvelopeStatus,
    RequestEnvelope,
    ResponseEnvelope,
)
from airunner_services.runtimes.contracts import (
    ArtInvocationRequest,
    RuntimeAction,
    RuntimeKind,
)
from airunner_services.runtimes.art_daemon_runtime_settings import (
    resolve_art_daemon_runtime_settings,
)
from airunner_services.runtimes.local_fallback._base import (
    DEFAULT_PROVIDER,
    ProgressCallback,
    _build_art_service,
    _build_signal_mediator,
    _model_status_value,
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
    _resolve_model_type,
    _SignalRuntimeClient,
)

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
        """Interrupt active art generation on a best-effort basis."""
        from airunner_services.contract_enums import SignalCode

        self._emit_signal(SignalCode.INTERRUPT_IMAGE_GENERATION_SIGNAL, {})
        return ResponseEnvelope(
            request_id=request_id,
            status=EnvelopeStatus.CANCELLED,
            metadata={"best_effort": True},
        )

    def _unload_model(self, request: RequestEnvelope) -> ResponseEnvelope:
        """Unload the current art pipeline or one supported component."""
        from airunner_services.contract_enums import ModelStatus, SignalCode

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
        """Generate art through the current callback-based worker flow."""
        from airunner_services.art.managers.stablediffusion.image_request import (
            ImageRequest,
        )
        from airunner_services.contract_enums import SignalCode

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
        signal_payload = {"image_request": image_request}
        active_rect = _resolve_art_active_rect(metadata)
        if active_rect is not None:
            signal_payload["active_rect"] = active_rect

        # Ensure the SD worker is created and registered for signals
        # before we emit DO_GENERATE_SIGNAL.  The worker is lazily
        # instantiated by ServiceWorkerManager; accessing it here
        # triggers creation and signal-handler registration so the
        # signal below is received.
        print(
            "[LocalFallbackArtClient] Creating SD worker and emitting "
            f"DO_GENERATE_SIGNAL model={image_request.model_path!r} "
            f"version={image_request.version!r}"
        )
        sd_worker = self._art_worker(create=True)
        if sd_worker is None:
            print(
                "[LocalFallbackArtClient] ERROR: SD worker could not "
                "be created (worker_manager not found on signal_source)"
            )
        else:
            print(
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
        try:
            self._emit_signal(
                SignalCode.DO_GENERATE_SIGNAL,
                signal_payload,
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

    def _art_worker(self, *, create: bool = False):
        """Return the art worker when one exists."""
        worker_manager = getattr(self._signal_source, "_worker_manager", None)
        if worker_manager is None:
            return None
        if create:
            return getattr(worker_manager, "sd_worker", None)
        return getattr(worker_manager, "_sd_worker", None)

    def _art_model_manager(self, *, create: bool = False):
        """Return the headless SD model manager when one exists."""
        worker = self._art_worker(create=create)
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
