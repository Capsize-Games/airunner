from PIL import Image
from PyQt6.QtCore import QObject

from airunner.mediator_mixin import MediatorMixin
from airunner.windows.main.settings_mixin import SettingsMixin


class SDRequest(
    QObject,
    MediatorMixin,
    SettingsMixin
):
    def __init__(self, *args, **kwargs):
        MediatorMixin.__init__(self)
        SettingsMixin.__init__(self)
        QObject.__init__(self)

    def __call__(
        self,
        model: dict,
        model_data: dict,
        settings: dict = None,
        override_data: dict = None,
        prompt: str = "",
        negative_prompt: str = "",
        action: str = "txt2img",
        active_rect: list = None,
        generator_section: str = "stablediffusion",
        enable_controlnet: bool = False,
        controlnet_image: Image = None,
        memory_options: dict = None,
        extra_options: dict = None
    ) -> dict:
        settings = settings if not settings else settings
        override_data = {} if not override_data else override_data
        extra_options = {} if not extra_options else extra_options

        if enable_controlnet:
            extra_options["controlnet_image"] = controlnet_image

        action = override_data.get("action", action)
        prompt = override_data.get("prompt", settings["generator_settings"]["prompt"])
        negative_prompt = override_data.get("negative_prompt", settings["generator_settings"]["negative_prompt"])
        steps = int(override_data.get("steps", settings["generator_settings"]["steps"]))
        strength = float(override_data.get("strength", settings["generator_settings"]["strength"] / 100.0))
        image_guidance_scale = float(override_data.get("image_guidance_scale", settings["generator_settings"][
            "image_guidance_scale"] / 10000.0 * 100.0))
        scale = float(override_data.get("scale", settings["generator_settings"]["scale"] / 100))
        seed = int(override_data.get("seed", settings["generator_settings"]["seed"]))
        ddim_eta = float(override_data.get("ddim_eta", settings["generator_settings"]["ddim_eta"]))
        n_iter = int(override_data.get("n_iter", 1))
        n_samples = int(override_data.get("n_samples", settings["generator_settings"]["n_samples"]))
        # iterate over all keys in model_data
        model_data = settings["generator_settings"]
        for k, v in override_data.items():
            if k.startswith("model_data_"):
                model_data[k.replace("model_data_", "")] = v
        scheduler = override_data.get("scheduler", settings["generator_settings"]["scheduler"])
        enable_controlnet = bool(
            override_data.get("enable_controlnet", settings["generator_settings"]["enable_controlnet"]))
        controlnet = override_data.get("controlnet", settings["generator_settings"]["controlnet_image_settings"]["controlnet"])
        controlnet_conditioning_scale = float(override_data.get("controlnet_conditioning_scale", settings["generator_settings"]["controlnet_image_settings"]["guidance_scale"]))
        width = int(override_data.get("width", settings["working_width"]))
        height = int(override_data.get("height", settings["working_height"]))
        clip_skip = int(override_data.get("clip_skip", settings["generator_settings"]["clip_skip"]))
        batch_size = int(override_data.get("batch_size", 1))

        model_data = {
            "name": model_data.get("name", model["name"]),
            "path": model_data.get("path", model["path"]),
            "branch": model_data.get("branch", model["branch"]),
            "version": model_data.get("version", model['version']),
            "category": model_data.get("category", model['category']),
            "pipeline_action": model_data.get("pipeline_action", model["pipeline_action"]),
            "enabled": model_data.get("enabled", model["enabled"]),
            "default": model_data.get("default", model["is_default"])
        }

        input_image = override_data.get("input_image", None),
        if input_image:
            # check if input image is a tupil
            if isinstance(input_image, tuple):
                input_image = input_image[0]

        original_model_data = {}
        if input_image is not None:
            if isinstance(input_image, tuple):
                input_image_info = input_image[0].info
            else:
                input_image_info = input_image.info

            keys = [
                "name",
                "path",
                "branch",
                "version",
                "category",
                "pipeline_action",
                "enabled",
                "default",
            ]
            original_model_data = {
                key: model_data.get(
                    key, input_image_info.get(key, "")) for key in keys
            }

        options = {
            "sd_request": True,
            "prompt": prompt,
            "negative_prompt": negative_prompt,
            "steps": steps,
            "ddim_eta": ddim_eta,  # only applies to ddim scheduler
            "n_iter": n_iter,
            "n_samples": n_samples,
            "scale": scale,
            "seed": seed,
            "model": model['name'],
            "model_data": model_data,
            "original_model_data": original_model_data,
            "scheduler": scheduler,
            "model_path": model["path"],
            "model_branch": model["branch"],
            # lora=self.available_lora(action),
            "generator_section": generator_section,
            "width": width,
            "height": height,
            "do_nsfw_filter": settings["nsfw_filter"],
            "pos_x": 0,
            "pos_y": 0,
            "outpaint_box_rect": active_rect,
            "hf_token": settings["hf_api_key_read_key"],
            "model_base_path": settings["path_settings"]["base_path"],
            "outpaint_model_path": settings["path_settings"]["inpaint_model_path"],
            "pix2pix_model_path": settings["path_settings"]["pix2pix_model_path"],
            "depth2img_model_path": settings["path_settings"]["depth2img_model_path"],
            "upscale_model_path": settings["path_settings"]["upscale_model_path"],
            "image_path": settings["path_settings"]["image_path"],
            "lora_path": settings["path_settings"]["lora_model_path"],
            "embeddings_path": settings["path_settings"]["embeddings_model_path"],
            "video_path": settings["path_settings"]["video_path"],
            "clip_skip": clip_skip,
            "batch_size": batch_size,
            "variation": settings["generator_settings"]["variation"],
            "deterministic_generation": False,
            "input_image": input_image,
            "enable_controlnet": enable_controlnet,
            "controlnet_conditioning_scale": controlnet_conditioning_scale,
            "controlnet": controlnet,
            "allow_online_mode": settings["allow_online_mode"],
            "hf_api_key_read_key": settings["hf_api_key_read_key"],
            "hf_api_key_write_key": settings["hf_api_key_write_key"],
            "unload_unused_model": settings["memory_settings"]["unload_unused_models"],
            "move_unused_model_to_cpu": settings["memory_settings"]["move_unused_model_to_cpu"],
        }

        if controlnet_image:
            options["controlnet_image"] = controlnet_image

        if action in ["txt2img", "img2img", "outpaint", "depth2img"]:
            options[f"strength"] = strength
        elif action in ["pix2pix"]:
            options[f"image_guidance_scale"] = image_guidance_scale

        return {
            "action": action,
            "options": {
                **options,
                **extra_options,
                **memory_options
            }
        }