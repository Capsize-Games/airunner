from airunner.components.application.api.api_service_base import APIServiceBase
from airunner.components.art.api.canvas_services import CanvasAPIService
from airunner.components.art.api.embedding_services import EmbeddingAPIServices
from airunner.components.art.api.image_filter_services import (
    ImageFilterAPIServices,
)
from airunner.components.art.api.lora_services import LoraAPIServices
from airunner.enums import SignalCode
from PIL.Image import Image
from airunner.components.art.managers.stablediffusion.image_request import (
    ImageRequest,
)
from airunner.enums import GeneratorSection
from typing import Optional, Dict, List


class ARTAPIService(APIServiceBase):
    """Art generation API service providing signal-based art operations."""

    def __init__(self):
        super().__init__()
        self.canvas = CanvasAPIService()
        self.embeddings = EmbeddingAPIServices()
        self.lora = LoraAPIServices()
        self.image_filter = ImageFilterAPIServices()

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
        image_request = data.get(
            "image_request", image_request or ImageRequest()
        )
        data.update({"image_request": image_request})
        self.emit_signal(SignalCode.DO_GENERATE_SIGNAL, data)

    def interrupt_generate(self):
        self.emit_signal(SignalCode.INTERRUPT_IMAGE_GENERATION_SIGNAL)

    def active_grid_area_updated(self):
        self.emit_signal(SignalCode.APPLICATION_ACTIVE_GRID_AREA_UPDATED)

    def update_generator_form_values(self):
        self.emit_signal(SignalCode.GENERATOR_FORM_UPDATE_VALUES_SIGNAL)
