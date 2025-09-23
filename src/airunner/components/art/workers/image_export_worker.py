import datetime
import os
from typing import Any, Dict, List, Optional
from airunner.components.application.workers.worker import Worker
from airunner.enums import QueueType
from airunner.components.art.managers.stablediffusion import (
    image_generation,
)


class ImageExportWorker(Worker):
    queue_type = QueueType.GET_LAST_ITEM

    def handle_message(self, message: Dict):
        images = message.get("images", [])
        data = message.get("data", {})
        self._export_images(images, data)

    def _export_images(self, images, data):
        application_settings = data.get("application_settings")
        path_settings = data.get("path_settings")
        if not application_settings.auto_export_images:
            return
        extension = application_settings.image_export_type
        filename = "image"
        file_path = os.path.expanduser(
            os.path.join(path_settings.image_path, f"{filename}.{extension}")
        )
        metadata = self._initialize_metadata(images, data)
        image_generation.export_images_with_metadata(
            images, file_path, metadata
        )

    def _initialize_metadata(
        self, images: List[Any], data: Dict
    ) -> Optional[dict]:
        metadata = None
        metadata_settings = data.get("metadata_settings")
        controlnet_settings = data.get("controlnet_settings")
        if metadata_settings.export_metadata:
            metadata_dict = {}
            if metadata_settings.image_export_metadata_prompt:
                metadata_dict["prompt"] = data.get("current_prompt", "")
                metadata_dict["prompt_2"] = data.get("current_prompt_2", "")
            if metadata_settings.image_export_metadata_negative_prompt:
                metadata_dict["negative_prompt"] = data.get(
                    "current_negative_prompt", ""
                )
                metadata_dict["negative_prompt_2"] = data.get(
                    "current_negative_prompt_2", ""
                )
            image_request = data.get("image_request")
            if metadata_settings.image_export_metadata_scale:
                metadata_dict["scale"] = data.get("guidance_scale", 0)
            if metadata_settings.image_export_metadata_seed:
                metadata_dict["seed"] = image_request.seed
            if metadata_settings.image_export_metadata_steps:
                metadata_dict["steps"] = image_request.steps
            if metadata_settings.image_export_metadata_ddim_eta:
                metadata_dict["ddim_eta"] = image_request.ddim_eta
            if metadata_settings.image_export_metadata_iterations:
                metadata_dict["num_inference_steps"] = data[
                    "num_inference_steps"
                ]
            if metadata_settings.image_export_metadata_samples:
                metadata_dict["n_samples"] = image_request.n_samples
            if metadata_settings.image_export_metadata_model:
                metadata_dict["model"] = data.get("model_path", "")
            if metadata_settings.image_export_metadata_version:
                metadata_dict["version"] = data.get("version", "")
            if metadata_settings.image_export_metadata_scheduler:
                metadata_dict["scheduler"] = data.get("scheduler_name", "")
            if metadata_settings.image_export_metadata_strength:
                metadata_dict["strength"] = data.get("strength", 0)
            if metadata_settings.image_export_metadata_lora:
                metadata_dict["lora"] = data.get("loaded_lora", [])
            if metadata_settings.image_export_metadata_embeddings:
                metadata_dict["embeddings"] = data.get("loaded_embeddings", [])
            if metadata_settings.image_export_metadata_timestamp:
                metadata_dict["timestamp"] = datetime.datetime.now(
                    datetime.timezone.utc
                ).isoformat()
            if (
                metadata_settings.image_export_metadata_controlnet
                and data.get("controlnet_enabled", False)
            ):
                metadata_dict.update(
                    {
                        "guess_mode": data["guess_mode"],
                        "control_guidance_start": data[
                            "control_guidance_start"
                        ],
                        "control_guidance_end": data["control_guidance_end"],
                        "controlnet_strength": data["strength"],
                        "controlnet_guidance_scale": data["guidance_scale"],
                        "controlnet_conditioning_scale": data[
                            "controlnet_conditioning_scale"
                        ],
                        "controlnet": controlnet_settings.controlnet,
                    }
                )
            if data.get("is_txt2img", False):
                metadata_dict["action"] = "txt2img"
            elif data.get("is_img2img", False):
                metadata_dict["action"] = "img2img"
            elif data.get("is_inpaint", False):
                metadata_dict.update(
                    {
                        "action": "inpaint",
                    }
                )
            elif data.get("is_outpaint", False):
                metadata_dict.update(
                    {
                        "action": "outpaint",
                        "mask_blur": data.get("mask_blur", 0),
                    }
                )
            memory_settings_flags = data.get("memory_settings_flags", {})
            metadata_dict["tome_sd"] = memory_settings_flags.get(
                "use_tome_sd", False
            )
            metadata_dict["tome_ratio"] = memory_settings_flags.get(
                "tome_ratio", 0.0
            )
            metadata = [metadata_dict for _ in range(len(images))]
        return metadata
