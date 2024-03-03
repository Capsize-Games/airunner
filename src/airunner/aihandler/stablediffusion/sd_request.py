import torch
from PIL import Image
from PyQt6.QtCore import QObject, QRect

from airunner.enums import SDMode, GeneratorSection, Controlnet
from airunner.mediator_mixin import MediatorMixin
from airunner.service_locator import ServiceLocator
from airunner.settings import DEFAULT_SCHEDULER
from airunner.utils import convert_base64_to_image
from airunner.windows.main.settings_mixin import SettingsMixin


class ControlnetImageSettings:
    def __init__(self, **data):
        self.imported_image_base64 = data.get("imported_image_base64", None)
        self.link_to_input_image = data.get("link_to_input_image", True)
        self.use_imported_image = data.get("use_imported_image", False)
        self.use_grid_image = data.get("use_grid_image", False)
        self.recycle_grid_image = data.get("recycle_grid_image", False)
        self.mask_link_input_image = data.get("mask_link_input_image", False)
        self.mask_use_imported_image = data.get("mask_use_imported_image", False)
        self.controlnet = data.get("controlnet", Controlnet.CANNY.value)
        self.conditioning_scale = data.get("conditioning_scale", 100) / 100.0
        self.guidance_scale = data.get("guidance_scale", 750 / 100.0)
        self.controlnet_image_base64 = data.get("controlnet_image_base64", None)


class GeneratorSettings:
    def __init__(self, **data):
        self.prompt = data.get("prompt", "")
        self.negative_prompt = data.get("negative_prompt", "")
        self.steps = data.get("steps", 1)
        self.ddim_eta = data.get("ddim_eta", 0.5)
        self.height = data.get("height", 512)
        self.width = data.get("width", 512)
        self.scale = data.get("scale", 0)
        self.seed = data.get("seed", 42)
        self.random_seed = data.get("random_seed", True)
        self.model = data.get("model", "stabilityai/sd-turbo")
        self.scheduler = data.get("scheduler", DEFAULT_SCHEDULER)
        self.prompt_triggers = data.get("prompt_triggers", "")
        self.strength = data.get("strength", 50) / 100.0
        self.image_guidance_scale = data.get("image_guidance_scale", 150) / 100.0
        self.n_samples = data.get("n_samples", 1)
        self.enable_controlnet = data.get("enable_controlnet", False)
        self.clip_skip = data.get("clip_skip", 0)
        self.variation = data.get("variation", False)
        self.use_prompt_builder = data.get("use_prompt_builder", False)
        self.active_grid_border_color = data.get("active_grid_border_color", "#00FF00")
        self.active_grid_fill_color = data.get("active_grid_fill_color", "#FF0000")
        self.version = data.get("version", "SD Turbo")
        self.is_preset = data.get("is_preset", False)
        self.input_image = data.get("input_image", None)
        self.section = data.get("section", "txt2img")
        self.generator_name = data.get("generator_name", "stablediffusion")
        self.controlnet_image_settings = self.controlnet_image_settings = ControlnetImageSettings(
            **data.get("controlnet_image_settings", {})
        )


class MemorySettings:
    def __init__(self, **data):
        self.use_last_channels = data.get("use_last_channels", True)
        self.use_attention_slicing = data.get("use_attention_slicing", False)
        self.use_tf32 = data.get("use_tf32", False)
        self.use_enable_vae_slicing = data.get("use_enable_vae_slicing", True)
        self.use_accelerated_transformers = data.get("use_accelerated_transformers", True)
        self.use_tiled_vae = data.get("use_tiled_vae", True)
        self.enable_model_cpu_offload = data.get("enable_model_cpu_offload", False)
        self.use_enable_sequential_cpu_offload = data.get("use_enable_sequential_cpu_offload", False)
        self.use_cudnn_benchmark = data.get("use_cudnn_benchmark", True)
        self.use_torch_compile = data.get("use_torch_compile", False)
        self.use_tome_sd = data.get("use_tome_sd", True)
        self.tome_sd_ratio = data.get("tome_sd_ratio", 600)
        self.move_unused_model_to_cpu = data.get("move_unused_model_to_cpu", False)
        self.unload_unused_models = data.get("unload_unused_models", True)


class SDRequest(
    QObject,
    MediatorMixin,
    SettingsMixin
):
    @property
    def drawing_pad_image(self):
        base_64_image = self.settings["drawing_pad_settings"]["image"]
        return convert_base64_to_image(base_64_image)

    @property
    def image(self):
        # current_layer_index = self.settings["current_layer_index"]
        # layer = self.settings["layers"][current_layer_index]
        # image = layer["base_64_image"]
        # return convert_base64_to_image(image)
        return self.drawing_pad_image

    def __init__(self, *args, **kwargs):
        QObject.__init__(self)
        MediatorMixin.__init__(self)
        SettingsMixin.__init__(self)
        self.model_data = kwargs.get("model_data", None)
        self.options = None
        self.do_set_seed = False
        self.generator_settings = None
        self.memory_settings = MemorySettings(**self.settings["memory_settings"])
        self.generator_settings = None
        self.action_has_safety_checker = False
        self.is_outpaint = False
        self.is_txt2img = False
        self.is_upscale = False
        self.is_img2img = False
        self.is_depth2img = False
        self.is_pix2pix = False
        self.load_generator_settings()

    def load_generator_settings(self):
        self.generator_settings = GeneratorSettings(**self.settings["generator_settings"])
        self.action_has_safety_checker = self.generator_settings.section not in [GeneratorSection.DEPTH2IMG.value]
        self.is_outpaint = self.generator_settings.section == GeneratorSection.OUTPAINT.value
        self.is_txt2img = False #self.generator_settings.section == GeneratorSection.TXT2IMG.value and self.drawing_pad_image is None
        self.is_upscale = self.generator_settings.section == GeneratorSection.UPSCALE.value
        self.is_img2img = True #self.generator_settings.section == GeneratorSection.TXT2IMG.value and self.drawing_pad_image is not None
        self.is_depth2img = self.generator_settings.section == GeneratorSection.DEPTH2IMG.value
        self.is_pix2pix = self.generator_settings.section == GeneratorSection.PIX2PIX.value

    def __call__(
        self,
        model: dict = None,
        model_data: dict = None,
        active_rect: list = None,
        memory_options: dict = None,
        extra_options: dict = None,
        sd_mode: SDMode = SDMode.STANDARD,
        strength=None,
        prompt_embeds=None,
        negative_prompt_embeds=None,
        callback=None,
        cross_attention_kwargs_scale=None,
        latents=None,
        device=None,
        do_load=False,
        generator=None,
        model_changed=False,
        controlnet_image=None
    ) -> dict:
        self.model_data = model_data
        self.memory_settings = MemorySettings(**self.settings["memory_settings"])
        if self.generator_settings is not None:
            self.do_set_seed = self.generator_settings.seed != self.settings["generator_settings"]["seed"]
        self.load_generator_settings()
        self.latents = latents
        self.callback_steps: int = 1
        self.cross_attention_kwargs_scale = cross_attention_kwargs_scale
        self.controlnet_image = controlnet_image
        self.model_changed = model_changed
        self.do_load = do_load
        self.generator = generator

        kwargs = self.prepare_args(
            model=model,
            model_data=model_data,
            active_rect=active_rect,
            controlnet_image=self.controlnet_image,
            memory_options=memory_options,
            extra_options=extra_options,
            sd_mode=sd_mode,
            strength=strength,
            prompt_embeds=prompt_embeds,
            negative_prompt_embeds=negative_prompt_embeds
        )
        args = {
            "num_inference_steps": self.generator_settings.steps,
            "guidance_scale": self.generator_settings.controlnet_image_settings.guidance_scale,
            "callback": callback,
            # "callback_on_step_end": self.callback,
        }

        args.update(kwargs)

        args["callback_steps"] = self.callback_steps
        args["clip_skip"] = self.generator_settings.clip_skip

        if self.cross_attention_kwargs_scale is not None:
            args["cross_attention_kwargs"] = {
                "scale": self.cross_attention_kwargs_scale
            }

        if self.generator_settings.enable_controlnet:
            args = {
                **args,
                **{
                    "control_image": self.controlnet_image,
                    "guess_mode": None,
                    "control_guidance_start": 0.0,
                    "control_guidance_end": 1.0,
                    "controlnet_conditioning_scale": self.generator_settings.controlnet_image_settings.conditioning_scale,
                }
            }

        if self.latents is not None:
            args["latents"] = self.latents

        if self.generator_settings.section == "pix2pix":
            args["image_guidance_scale"] = self.generator_settings.image_guidance_scale
            args["generator"] = self.generator
            del args["latents"]

        if self.is_img2img and self.generator_settings.enable_controlnet:
            args["height"] = self.generator_settings.height
            args["width"] = self.generator_settings.width
            if args["num_inference_steps"] < 3:
                args["num_inference_steps"] = 3
            args["generator"] = self.generator

        return args

    def prepare_args(
        self,
        model: dict = None,
        model_data: dict = None,
        active_rect: list = None,
        controlnet_image: Image = None,
        memory_options: dict = None,
        extra_options: dict = None,
        sd_mode: SDMode = SDMode.STANDARD,
        strength=None,
        prompt_embeds=None,
        negative_prompt_embeds=None,
    ) -> dict:
        extra_options = {} if not extra_options else extra_options

        if strength is None:
            strength = self.generator_settings.strength

        if model is None:
            name = model_data["name"] if "name" in model_data else self.generator_settings.model
            model = ServiceLocator.get("ai_model_by_name")(name)

        if self.generator_settings.enable_controlnet:
            extra_options["controlnet_image"] = controlnet_image

        if active_rect is None:
            active_rect = QRect(
                self.settings["active_grid_settings"]["pos_x"],
                self.settings["active_grid_settings"]["pos_y"],
                self.settings["active_grid_settings"]["width"],
                self.settings["active_grid_settings"]["height"]
            )
            active_rect.translate(
                -self.settings["canvas_settings"]["pos_x"],
                -self.settings["canvas_settings"]["pos_y"]
            )

        guidance_scale = self.generator_settings.controlnet_image_settings.guidance_scale
        controlnet_conditioning_scale = float(self.generator_settings.controlnet_image_settings.conditioning_scale)
        steps = int(self.generator_settings.steps)
        image_guidance_scale = float(self.generator_settings.image_guidance_scale / 10000.0 * 100.0)
        scale = float(self.generator_settings.scale / 100)
        seed = int(self.generator_settings.seed)
        ddim_eta = float(self.generator_settings.ddim_eta)
        n_iter = int(self.generator_settings.steps)
        n_samples = int(self.generator_settings.n_samples)
        scheduler = self.generator_settings.scheduler
        enable_controlnet = bool(self.generator_settings.enable_controlnet)
        controlnet = self.generator_settings.controlnet_image_settings.controlnet
        width = int(self.settings["working_width"])
        height = int(self.settings["working_height"])
        clip_skip = int(self.generator_settings.clip_skip)
        batch_size = int(1)
        self.mask = None
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

        input_image = None
        base64image = self.settings["drawing_pad_settings"]["image"]
        if base64image:
            input_image = convert_base64_to_image(base64image).convert("RGBA")

        options = {
            "sd_request": True,
            "empty_queue": False,
            "steps": steps,
            "ddim_eta": ddim_eta,  # only applies to ddim scheduler
            "n_iter": n_iter,
            "n_samples": n_samples,
            "scale": scale,
            "seed": seed,
            "model": model['name'],
            "model_data": model_data,
            "original_model_data": {},
            "scheduler": scheduler,
            "model_path": model["path"],
            "model_branch": model["branch"],
            # lora=self.available_lora(action),
            "width": width,
            "height": height,
            "pos_x": 0,
            "pos_y": 0,
            "outpaint_box_rect": active_rect,
            "hf_token": self.settings["hf_api_key_read_key"],
            "model_base_path": self.settings["path_settings"]["base_path"],
            "outpaint_model_path": self.settings["path_settings"]["inpaint_model_path"],
            "pix2pix_model_path": self.settings["path_settings"]["pix2pix_model_path"],
            "depth2img_model_path": self.settings["path_settings"]["depth2img_model_path"],
            "upscale_model_path": self.settings["path_settings"]["upscale_model_path"],
            "image_path": self.settings["path_settings"]["image_path"],
            "lora_path": self.settings["path_settings"]["lora_model_path"],
            "lora": self.settings["lora"],
            "embeddings_path": self.settings["path_settings"]["embeddings_model_path"],
            "video_path": self.settings["path_settings"]["video_path"],
            "clip_skip": clip_skip,
            "batch_size": batch_size,
            "variation": self.settings["generator_settings"]["variation"],
            "deterministic_generation": False,
            "input_image": input_image,
            "enable_controlnet": enable_controlnet,
            "controlnet": controlnet,
            "allow_online_mode": self.settings["allow_online_mode"],
            "hf_api_key_read_key": self.settings["hf_api_key_read_key"],
            "hf_api_key_write_key": self.settings["hf_api_key_write_key"],
            "unload_unused_model": self.settings["memory_settings"]["unload_unused_models"],
            "move_unused_model_to_cpu": self.settings["memory_settings"]["move_unused_model_to_cpu"],
            "auto_export_images": self.settings["auto_export_images"],
            "guidance_scale": guidance_scale,
            "controlnet_conditioning_scale": controlnet_conditioning_scale,
            "sd_mode": sd_mode,
        }

        if controlnet_image:
            options["controlnet_image"] = controlnet_image

        if self.generator_settings.section in ["txt2img", "img2img", "outpaint", "depth2img"]:
            options[f"strength"] = strength
        elif self.generator_settings.section in ["pix2pix"]:
            options[f"image_guidance_scale"] = image_guidance_scale

        if memory_options is None:
            memory_options = {
                "use_last_channels": self.settings["memory_settings"]["use_last_channels"],
                "use_enable_sequential_cpu_offload": self.settings["memory_settings"][
                "use_enable_sequential_cpu_offload"],
                "enable_model_cpu_offload": self.settings["memory_settings"]["enable_model_cpu_offload"],
                "use_attention_slicing": self.settings["memory_settings"]["use_attention_slicing"],
                "use_tf32": self.settings["memory_settings"]["use_tf32"],
                "use_cudnn_benchmark": self.settings["memory_settings"]["use_cudnn_benchmark"],
                "use_enable_vae_slicing": self.settings["memory_settings"]["use_enable_vae_slicing"],
                "use_accelerated_transformers": self.settings["memory_settings"]["use_accelerated_transformers"],
                "use_torch_compile": self.settings["memory_settings"]["use_torch_compile"],
                "use_tiled_vae": self.settings["memory_settings"]["use_tiled_vae"],
                "use_tome_sd": self.settings["memory_settings"]["use_tome_sd"],
                "tome_sd_ratio": self.settings["memory_settings"]["tome_sd_ratio"],
            }

        args = {
            "action": self.generator_settings.section,
            "options": {
                **options,
                **extra_options,
                **memory_options
            }
        }

        args = self.load_prompt_embed_args(
            prompt_embeds,
            negative_prompt_embeds,
            args
        )

        extra_args = self.prepare_extra_args(self.image, self.mask)

        return {**args, **extra_args}

    def prepare_extra_args(self, image, mask):
        extra_args = {
        }
        if self.is_txt2img:
            extra_args = {**extra_args, **{
                "width": self.generator_settings.width,
                "height": self.generator_settings.height,
            }}
        if self.is_img2img:
            extra_args = {**extra_args, **{
                "image": image,
                "strength": self.generator_settings.strength,
            }}
        elif self.is_pix2pix:
            extra_args = {**extra_args, **{
                "image": image,
                "image_guidance_scale": self.generator_settings.image_guidance_scale,
            }}
        elif self.is_depth2img:
            extra_args = {**extra_args, **{
                "image": image,
                "strength": self.generator_settings.strength,
                #"depth_map": self.depth_map
            }}
        elif self.is_upscale:
            extra_args = {**extra_args, **{
                "image": image
            }}
        elif self.is_outpaint:
            extra_args = {**extra_args, **{
                "image": image,
                "mask_image": mask,
                "width": self.generator_settings.width,
                "height": self.generator_settings.height,
            }}
        return extra_args

    def load_prompt_embed_args(
        self,
        prompt_embeds,
        negative_prompt_embeds,
        args
    ):
        """
        Load prompt embeds
        """
        if prompt_embeds is not None and negative_prompt_embeds is not None:
            args["prompt_embeds"] = prompt_embeds
            args["negative_prompt_embeds"] = negative_prompt_embeds
            if "prompt" in args:
                del args["prompt"]
            if "negative_prompt" in args:
                del args["negative_prompt"]
        else:
            args["prompt"] = self.generator_settings.prompt
            args["negative_prompt"] = self.generator_settings.negative_prompt
        return args


class UpscaleRequest(SDRequest):
    def prepare_args(self, **kwargs) -> dict:
        args = super().prepare_args(**kwargs)
        args.update({
            "image": kwargs.get("image"),
            "generator": self.generator,
        })

    def load_prompt_embed_args(
        self,
        prompt_embeds,
        negative_prompt_embeds,
        args
    ):
        """
        Load prompt embeds
        """
        args["prompt"] = self.generator_settings.prompt
        args["negative_prompt"] = self.generator_settings.negative_prompt
        return args
