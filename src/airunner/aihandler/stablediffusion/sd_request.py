from PIL import Image
from PySide6.QtCore import QObject, QRect

from airunner.enums import SDMode, GeneratorSection, Controlnet
from airunner.mediator_mixin import MediatorMixin
from airunner.settings import DEFAULT_SCHEDULER, MIN_NUM_INFERENCE_STEPS_IMG2IMG
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
        self.guidance_scale = data.get("guidance_scale", 750) / 100.0
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
        return self.drawing_pad_image

    def __init__(self, *args, **kwargs):
        QObject.__init__(self)
        MediatorMixin.__init__(self)
        SettingsMixin.__init__(self)
        self.model_data = kwargs.get("model_data", None)
        self.do_set_seed = False
        self.memory_settings = MemorySettings(**self.settings["memory_settings"])
        self.generator_settings = None
        self.action_has_safety_checker = False
        self.is_outpaint = False
        self.is_txt2img = False
        self.is_upscale = False
        self.is_img2img = False
        self.is_depth2img = False
        self.is_pix2pix = False
        self.active_rect = None
        self.parent = None
        self.prompt_embeds = None
        self.negative_prompt_embeds = None
        self.load_generator_settings()

    def load_generator_settings(self):
        self.generator_settings = GeneratorSettings(**self.settings["generator_settings"])
        self.action_has_safety_checker = self.generator_settings.section not in [GeneratorSection.DEPTH2IMG.value]

    def initialize_prompt_embeds(self, prompt_embeds, negative_prompt_embeds, args: dict):
        self.prompt_embeds = prompt_embeds
        self.negative_prompt_embeds = negative_prompt_embeds
        args = self.load_prompt_embed_args(
            prompt_embeds,
            negative_prompt_embeds,
            args
        )
        return args

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
        controlnet_image=None,
        generator_request_data: dict = None,
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
            negative_prompt_embeds=negative_prompt_embeds,
            generator_request_data=generator_request_data
        )

        input_image = kwargs["image"] if "image" in kwargs else None
        self.is_outpaint = self.generator_settings.section == GeneratorSection.OUTPAINT.value
        self.is_txt2img = self.generator_settings.section == GeneratorSection.TXT2IMG.value and input_image is None
        self.is_upscale = self.generator_settings.section == GeneratorSection.UPSCALE.value
        self.is_img2img = self.generator_settings.section == GeneratorSection.TXT2IMG.value and input_image is not None
        self.is_depth2img = self.generator_settings.section == GeneratorSection.DEPTH2IMG.value
        self.is_pix2pix = self.generator_settings.section == GeneratorSection.PIX2PIX.value
        args = {
            "num_inference_steps": self.generator_settings.steps,
            "callback": callback,
        }

        args.update(kwargs)
        args["callback_steps"] = self.callback_steps
        args["clip_skip"] = self.generator_settings.clip_skip

        if self.is_img2img or self.is_depth2img or self.is_pix2pix or self.is_outpaint:
            args["height"] = self.settings["working_height"]
            args["width"] = self.settings["working_width"]
            if self.is_img2img:
                if args["num_inference_steps"] < MIN_NUM_INFERENCE_STEPS_IMG2IMG:
                    args["num_inference_steps"] = MIN_NUM_INFERENCE_STEPS_IMG2IMG

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
        generator_request_data=None
    ) -> dict:
        extra_options = {} if not extra_options else extra_options

        if self.generator_settings.enable_controlnet and controlnet_image:
            extra_options["controlnet_image"] = controlnet_image

        self.active_rect = active_rect

        if self.active_rect is None:
            self.active_rect = QRect(
                self.settings["active_grid_settings"]["pos_x"],
                self.settings["active_grid_settings"]["pos_y"],
                self.settings["working_width"],
                self.settings["working_height"],
            )
            self.active_rect.translate(
                -self.settings["canvas_settings"]["pos_x"],
                -self.settings["canvas_settings"]["pos_y"]
            )

        width = int(self.settings["working_width"])
        height = int(self.settings["working_height"])
        clip_skip = int(self.generator_settings.clip_skip)

        args = {
            "action": self.generator_settings.section,
            "outpaint_box_rect": self.active_rect,
            "width": width,
            "height": height,
            "clip_skip": clip_skip,
        }

        args = self.load_prompt_embed_args(
            prompt_embeds,
            negative_prompt_embeds,
            args
        )

        extra_args = self.prepare_extra_args(generator_request_data)

        return {**args, **extra_args}

    def prepare_extra_args(self, generator_request_data):
        extra_args = {
        }
        width = int(self.settings["working_width"])
        height = int(self.settings["working_height"])

        image = None
        mask = None
        if generator_request_data is not None:
            if "image" in generator_request_data:
                image = generator_request_data["image"]
            if "mask" in generator_request_data:
                mask = generator_request_data["mask"]

        if image is None and not self.is_outpaint:
            base64image = self.settings["drawing_pad_settings"]["image"]
            if base64image != "":
                image = convert_base64_to_image(base64image)
                if image is not None:
                    image = image.convert("RGB")

        if self.is_txt2img:
            extra_args = {**extra_args, **{
                "width": width,
                "height": height,
            }}
        if self.is_img2img or self.is_depth2img:
            extra_args = {**extra_args, **{
                "strength": self.generator_settings.strength,
            }}
        elif self.is_pix2pix:
            extra_args = {**extra_args, **{
                "image_guidance_scale": self.generator_settings.strength,
            }}
        elif self.is_upscale:
            extra_args = {**extra_args, **{
                "image": image,
            }}
        elif self.is_outpaint:
            if image is None:
                base64image = self.settings["canvas_settings"]["image"]
                if base64image != "":
                    image = convert_base64_to_image(base64image)
                    if image is not None:
                        image = image.convert("RGB")
                    else:
                        print("IMAGE IS NONE")
            if mask is None:
                base64image = self.settings["canvas_settings"]["mask"]
                if base64image != "":
                    mask = convert_base64_to_image(base64image)
                    if mask is not None:
                        mask = mask.convert("RGB")
                    else:
                        print("IMAGE IS NONE")
            extra_args = {**extra_args, **{
                "width": self.generator_settings.width,
                "height": self.generator_settings.height,
            }}

        if image is not None:
            extra_args["image"] = image

        if mask is not None:
            extra_args["mask_image"] = mask

        controlnet_image = self.controlnet_image
        if self.generator_settings.enable_controlnet and controlnet_image:
            extra_args = {**extra_args, **{
                #"control_image": controlnet_image,
                "guess_mode": None,
                "control_guidance_start": 0.0,
                "control_guidance_end": 1.0,
                "guidance_scale": self.generator_settings.controlnet_image_settings.guidance_scale,
                "controlnet_conditioning_scale": self.generator_settings.controlnet_image_settings.conditioning_scale,
                "controlnet": [
                    "canny",
                    self.generator_settings.controlnet_image_settings.controlnet
                ],
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

    def disable_controlnet(self, data: dict) -> dict:
        """
        Remove controlnet settings from data
        :param data:
        :return:
        """
        for key in [
            "control_image",
            "guess_mode",
            "control_guidance_start",
            "control_guidance_end",
            "guidance_scale",
            "controlnet_conditioning_scale",
            "controlnet",
        ]:
            if key in data:
                del data[key]
        return data

    def disable_img2img(self, data: dict) -> dict:
        """
        Remove img2img settings from data
        :param data:
        :return:
        """
        for key in [
            "strength",
            "image"
        ]:
            if key in data:
                del data[key]
        return data


class UpscaleRequest(SDRequest):
    def prepare_args(self, **kwargs) -> dict:
        args = super().prepare_args(**kwargs)
        args.update({
            "image": kwargs.get("image"),
            "generator": self.generator,
        })
        return args

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
