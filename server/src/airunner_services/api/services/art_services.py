from __future__ import annotations

from typing import TYPE_CHECKING, Dict, List, Optional

from airunner_services.contract_enums import GeneratorSection
from airunner_services.api.api_service_base import APIServiceBase
from airunner_services.model_management import ModelResourceManager, ModelState
from airunner_services.utils.application.enum_resolver import signal_code_proxy

SignalCode = signal_code_proxy()

if TYPE_CHECKING:
    from PIL.Image import Image

    from airunner_services.api.services.canvas_services import CanvasAPIService
    from airunner_services.api.services.image_filter_services import (
        ImageFilterAPIServices,
    )
    from airunner_services.art.managers.stablediffusion.image_request import (
        ImageRequest,
    )


class ARTAPIService(APIServiceBase):
    """Art generation API service providing signal-based art operations."""

    def __init__(self) -> None:
        super().__init__()
        self._canvas_service = None
        self._image_filter_service = None

    @property
    def canvas(self) -> CanvasAPIService:
        """Return the cached canvas API service."""
        if self._canvas_service is None:
            from airunner_services.api.services.canvas_services import (
                CanvasAPIService,
            )

            self._canvas_service = CanvasAPIService()
        return self._canvas_service

    @canvas.setter
    def canvas(self, value: CanvasAPIService) -> None:
        self._canvas_service = value

    @property
    def image_filter(self) -> ImageFilterAPIServices:
        """Return the cached image-filter API service."""
        if self._image_filter_service is None:
            from airunner_services.api.services.image_filter_services import (
                ImageFilterAPIServices,
            )

            self._image_filter_service = ImageFilterAPIServices()
        return self._image_filter_service

    @image_filter.setter
    def image_filter(
        self,
        value: ImageFilterAPIServices,
    ) -> None:
        self._image_filter_service = value

    def update_batch_images(self, images: List[Image]) -> None:
        """Emit one batch-image update signal."""
        self.emit_signal(
            SignalCode.SD_UPDATE_BATCH_IMAGES_SIGNAL,
            {"images": images},
        )

    def save_prompt(
        self,
        prompt: str,
        negative_prompt: str,
        secondary_prompt: str,
        secondary_negative_prompt: str,
    ) -> None:
        """Persist one prompt selection through the shared signal bus."""
        self.emit_signal(
            SignalCode.SD_SAVE_PROMPT_SIGNAL,
            {
                "prompt": prompt,
                "negative_prompt": negative_prompt,
                "secondary_prompt": secondary_prompt,
                "secondary_negative_prompt": secondary_negative_prompt,
            },
        )

    def load(self, saved_prompt: Optional[str] = None) -> None:
        """Load one saved art prompt by name."""
        self.emit_signal(
            SignalCode.SD_LOAD_PROMPT_SIGNAL,
            {"saved_prompt": saved_prompt},
        )

    def unload(self) -> None:
        """Request one art-model unload through the shared signal bus."""
        self.emit_signal(SignalCode.SD_UNLOAD_SIGNAL)

    def model_changed(
        self,
        model: Optional[str],
        version: Optional[str] = None,
        pipeline: Optional[str] = None,
    ) -> None:
        """Emit one art-model change notification."""
        data = {}
        if model is not None:
            data["model"] = model
        if version is not None:
            data["version"] = version
        if pipeline is not None:
            data["pipeline"] = pipeline
        self.emit_signal(SignalCode.SD_ART_MODEL_CHANGED, data)

    def change_scheduler(self, val: str) -> None:
        """Emit one scheduler-change request."""
        self.emit_signal(
            SignalCode.CHANGE_SCHEDULER_SIGNAL,
            {"scheduler": val},
        )

    def final_progress_update(self, total: int) -> None:
        """Emit one terminal progress update."""
        self.progress_update(total, total)

    def progress_update(self, step: int, total: int) -> None:
        """Emit one art-generation progress update."""
        self.emit_signal(
            SignalCode.SD_PROGRESS_SIGNAL,
            {"step": step, "total": total},
        )

    def pipeline_loaded(self, section: GeneratorSection) -> None:
        """Emit one pipeline-loaded notification."""
        self.emit_signal(
            SignalCode.SD_PIPELINE_LOADED_SIGNAL,
            {"generator_section": section},
        )

    def generate_image_signal(self) -> None:
        """Emit one image-generation trigger."""
        self.emit_signal(SignalCode.SD_GENERATE_IMAGE_SIGNAL)

    def llm_image_generated(
        self,
        prompt: str,
        second_prompt: str,
        section: GeneratorSection,
        width: int,
        height: int,
    ) -> None:
        """Emit one LLM-produced image prompt payload."""
        self.emit_signal(
            SignalCode.LLM_IMAGE_PROMPT_GENERATED_SIGNAL,
            {
                "message": {
                    "prompt": prompt,
                    "second_prompt": second_prompt,
                    "image_type": section,
                    "width": width,
                    "height": height,
                }
            },
        )

    def stop_progress_bar(self) -> None:
        """Emit one request to stop the art progress UI."""
        self.emit_signal(
            SignalCode.APPLICATION_STOP_SD_PROGRESS_BAR_SIGNAL,
        )

    def clear_progress_bar(self) -> None:
        """Emit one request to clear the art progress UI."""
        self.emit_signal(
            SignalCode.APPLICATION_STOP_SD_PROGRESS_BAR_SIGNAL,
            {"do_clear": True},
        )

    @staticmethod
    def _mark_requested_model_loading(
        image_request: Optional[ImageRequest],
    ) -> None:
        """Track one requested art model in the shared resource state."""
        model_path = str(
            getattr(image_request, "model_path", "") or ""
        ).strip()
        if not model_path:
            return

        resource_manager = ModelResourceManager()
        current_state = resource_manager.get_model_state(model_path)
        if current_state in (ModelState.LOADED, ModelState.BUSY):
            return

        resource_manager.set_model_state(
            model_path,
            ModelState.LOADING,
            "text_to_image",
        )

    def missing_required_models(self, message: str) -> None:
        """Emit one missing-models notification."""
        self.emit_signal(
            SignalCode.MISSING_REQUIRED_MODELS,
            {"title": "Model Not Found", "message": message},
        )

    def send_request(
        self,
        image_request: Optional[ImageRequest] = None,
        data: Optional[Dict] = None,
    ) -> None:
        """Emit one art-generation request payload."""
        payload = data or {}

        if "image_request" in payload and payload["image_request"] is not None:
            resolved_request = payload["image_request"]
        elif image_request is not None:
            resolved_request = image_request
        else:
            raise ValueError("image_request is required for art requests")

        self._mark_requested_model_loading(resolved_request)
        payload.update({"image_request": resolved_request})
        self.emit_signal(SignalCode.DO_GENERATE_SIGNAL, payload)

    def interrupt_generate(self) -> None:
        """Emit one request to interrupt art generation."""
        self.emit_signal(SignalCode.INTERRUPT_IMAGE_GENERATION_SIGNAL)

    def active_grid_area_updated(self) -> None:
        """Emit one active-grid update notification."""
        self.emit_signal(SignalCode.APPLICATION_ACTIVE_GRID_AREA_UPDATED)

    def update_generator_form_values(self) -> None:
        """Emit one request to refresh art generator form values."""
        self.emit_signal(SignalCode.GENERATOR_FORM_UPDATE_VALUES_SIGNAL)
