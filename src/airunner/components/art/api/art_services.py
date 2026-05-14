from __future__ import annotations

from typing import TYPE_CHECKING, Dict, List, Optional

from airunner.components.application.api.api_service_base import APIServiceBase
from airunner.components.model_management import ModelResourceManager
from airunner.components.model_management.types import ModelState
from airunner.enums import GeneratorSection, SignalCode

if TYPE_CHECKING:
    from PIL.Image import Image
    from airunner.components.art.api.canvas_services import CanvasAPIService
    from airunner.components.art.api.embedding_services import (
        EmbeddingAPIServices,
    )
    from airunner.components.art.api.image_filter_services import (
        ImageFilterAPIServices,
    )
    from airunner.components.art.api.lora_services import LoraAPIServices
    from airunner.components.art.managers.stablediffusion.image_request import (
        ImageRequest,
    )


class ARTAPIService(APIServiceBase):
    """Art generation API service providing signal-based art operations."""

    def __init__(self):
        super().__init__()
        self._canvas_service = None
        self._embeddings_service = None
        self._lora_service = None
        self._image_filter_service = None

    @property
    def canvas(self) -> CanvasAPIService:
        """Return the cached canvas API service."""
        if self._canvas_service is None:
            from airunner.components.art.api.canvas_services import (
                CanvasAPIService,
            )

            self._canvas_service = CanvasAPIService()
        return self._canvas_service

    @canvas.setter
    def canvas(self, value: CanvasAPIService) -> None:
        self._canvas_service = value

    @property
    def embeddings(self) -> EmbeddingAPIServices:
        """Return the cached embeddings API service."""
        if self._embeddings_service is None:
            from airunner.components.art.api.embedding_services import (
                EmbeddingAPIServices,
            )

            self._embeddings_service = EmbeddingAPIServices()
        return self._embeddings_service

    @embeddings.setter
    def embeddings(self, value: EmbeddingAPIServices) -> None:
        self._embeddings_service = value

    @property
    def lora(self) -> LoraAPIServices:
        """Return the cached LoRA API service."""
        if self._lora_service is None:
            from airunner.components.art.api.lora_services import (
                LoraAPIServices,
            )

            self._lora_service = LoraAPIServices()
        return self._lora_service

    @lora.setter
    def lora(self, value: LoraAPIServices) -> None:
        self._lora_service = value

    @property
    def image_filter(self) -> ImageFilterAPIServices:
        """Return the cached image-filter API service."""
        if self._image_filter_service is None:
            from airunner.components.art.api.image_filter_services import (
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

    def update_batch_images(self, images: List[Image]):
        self.emit_signal(
            SignalCode.SD_UPDATE_BATCH_IMAGES_SIGNAL, {"images": images}
        )

    def save_prompt(
        self,
        prompt,
        negative_prompt,
        secondary_prompt,
        secondary_negative_prompt,
    ):
        self.emit_signal(
            SignalCode.SD_SAVE_PROMPT_SIGNAL,
            {
                "prompt": prompt,
                "negative_prompt": negative_prompt,
                "secondary_prompt": secondary_prompt,
                "secondary_negative_prompt": secondary_negative_prompt,
            },
        )

    def load(self, saved_prompt: Optional[str] = None):
        self.emit_signal(
            SignalCode.SD_LOAD_PROMPT_SIGNAL, {"saved_prompt": saved_prompt}
        )

    def unload(self):
        self.emit_signal(SignalCode.SD_UNLOAD_SIGNAL)

    def model_changed(
        self,
        model: Optional[str],
        version: Optional[str] = None,
        pipeline: Optional[str] = None,
    ):
        data = {}
        if model is not None:
            data["model"] = model
        if version is not None:
            data["version"] = version
        if pipeline is not None:
            data["pipeline"] = pipeline
        self.emit_signal(SignalCode.SD_ART_MODEL_CHANGED, data)

    def change_scheduler(self, val: str):
        self.emit_signal(
            SignalCode.CHANGE_SCHEDULER_SIGNAL, {"scheduler": val}
        )

    def lora_updated(self):
        self.emit_signal(SignalCode.LORA_UPDATED_SIGNAL, {})

    def embedding_updated(self):
        self.emit_signal(SignalCode.EMBEDDING_UPDATED_SIGNAL, {})

    def final_progress_update(self, total: int):
        self.progress_update(total, total)

    def progress_update(self, step: int, total: int):
        self.emit_signal(
            SignalCode.SD_PROGRESS_SIGNAL, {"step": step, "total": total}
        )

    def pipeline_loaded(self, section: GeneratorSection):
        self.emit_signal(
            SignalCode.SD_PIPELINE_LOADED_SIGNAL,
            {"generator_section": section},
        )

    def generate_image_signal(self):
        self.emit_signal(SignalCode.SD_GENERATE_IMAGE_SIGNAL)

    def llm_image_generated(
        self, prompt, second_prompt, section, width, height
    ):
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

    def stop_progress_bar(self):
        self.emit_signal(SignalCode.APPLICATION_STOP_SD_PROGRESS_BAR_SIGNAL)

    def clear_progress_bar(self):
        self.emit_signal(
            SignalCode.APPLICATION_STOP_SD_PROGRESS_BAR_SIGNAL,
            {"do_clear": True},
        )

    @staticmethod
    def _mark_requested_model_loading(
        image_request: Optional[ImageRequest],
    ) -> None:
        """Track the requested art model in the shared resource widget."""
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

    def missing_required_models(self, message: str):
        self.emit_signal(
            SignalCode.MISSING_REQUIRED_MODELS,
            {"title": "Model Not Found", "message": message},
        )

    def send_request(
        self,
        image_request: Optional[ImageRequest] = None,
        data: Optional[Dict] = None,
    ):
        data = data or {}

        if "image_request" in data and data["image_request"] is not None:
            resolved_request = data["image_request"]
        elif image_request is not None:
            resolved_request = image_request
        else:
            # Default to a request built from current canvas + generator settings.
            # This is critical for img2img/outpaint/controlnet since those settings
            # live outside generator_settings and determine generator_section, image, strength, etc.
            resolved_request = self.canvas.create_image_request()

        self._mark_requested_model_loading(resolved_request)
        data.update({"image_request": resolved_request})
        self.emit_signal(SignalCode.DO_GENERATE_SIGNAL, data)

    def interrupt_generate(self):
        self.emit_signal(SignalCode.INTERRUPT_IMAGE_GENERATION_SIGNAL)

    def active_grid_area_updated(self):
        self.emit_signal(SignalCode.APPLICATION_ACTIVE_GRID_AREA_UPDATED)

    def update_generator_form_values(self):
        self.emit_signal(SignalCode.GENERATOR_FORM_UPDATE_VALUES_SIGNAL)
