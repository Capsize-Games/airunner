from PIL import Image
from PySide6.QtCore import (
    QObject,
    QRect
)
from airunner.enums import (
    SDMode,
    GeneratorSection,
    ImagePreset
)
from airunner.mediator_mixin import MediatorMixin
from airunner.settings import (
    MIN_NUM_INFERENCE_STEPS_IMG2IMG,
    STABLEDIFFUSION_GENERATOR_SETTINGS, DEFAULT_GENERATOR_SETTINGS, DEFAULT_MEMORY_SETTINGS
)
from airunner.utils.convert_base64_to_image import convert_base64_to_image
from airunner.windows.main.settings_mixin import SettingsMixin


class ControlnetImageSettings:
    def __init__(self, **data):
        self.imported_image_base64 = data.get("imported_image_base64", DEFAULT_GENERATOR_SETTINGS["controlnet_image_settings"]["imported_image_base64"])
        self.link_to_input_image = data.get("link_to_input_image", DEFAULT_GENERATOR_SETTINGS["controlnet_image_settings"]["link_to_input_image"])
        self.use_imported_image = data.get("use_imported_image", DEFAULT_GENERATOR_SETTINGS["controlnet_image_settings"]["use_imported_image"])
        self.use_grid_image = data.get("use_grid_image", DEFAULT_GENERATOR_SETTINGS["controlnet_image_settings"]["use_grid_image"])
        self.recycle_grid_image = data.get("recycle_grid_image", DEFAULT_GENERATOR_SETTINGS["controlnet_image_settings"]["recycle_grid_image"])
        self.mask_link_input_image = data.get("mask_link_input_image", DEFAULT_GENERATOR_SETTINGS["controlnet_image_settings"]["mask_link_input_image"])
        self.mask_use_imported_image = data.get("mask_use_imported_image", DEFAULT_GENERATOR_SETTINGS["controlnet_image_settings"]["mask_use_imported_image"])
        self.controlnet = data.get("controlnet", DEFAULT_GENERATOR_SETTINGS["controlnet_image_settings"]["controlnet"])
        self.conditioning_scale = data.get("conditioning_scale", DEFAULT_GENERATOR_SETTINGS["controlnet_image_settings"]["conditioning_scale"]) / 100.0
        self.guidance_scale = data.get("guidance_scale", DEFAULT_GENERATOR_SETTINGS["controlnet_image_settings"]["guidance_scale"]) / 1000.0
        self.controlnet_image_base64 = data.get("controlnet_image_base64", DEFAULT_GENERATOR_SETTINGS["controlnet_image_settings"]["controlnet_image_base64"])


# class GeneratorSettings:
#     @property
#     def image_preset(self):
#         return self.generator_settings.get("image_preset", "")
#
#     @property
#     def prompt(self):
#         prompt = ""
#         if self.image_preset != "":
#             preset_enum = ImagePreset(self.image_preset)
#             if preset_enum is ImagePreset.ILLUSTRATION:
#                 prompt = "A beautiful illustration of a"
#             elif preset_enum is ImagePreset.PHOTOGRAPH:
#                 prompt = "A beautiful photograph of a"
#             elif preset_enum is ImagePreset.PAINTING:
#                 prompt = "A beautiful painting of a"
#         return f"{prompt} {self._prompt}"
#
#     @prompt.setter
#     def prompt(self, value):
#         self._prompt = value
#
#     @property
#     def negative_prompt(self):
#         negative_prompt = ""
#         if self.image_preset != "":
#             preset_enum = ImagePreset(self.image_preset)
#             if preset_enum is ImagePreset.ILLUSTRATION:
#                 negative_prompt = "photograph, realistic, photo realistic, ultra realistic, cgi"
#             elif preset_enum is ImagePreset.PHOTOGRAPH:
#                 negative_prompt = "illustration, drawing, painting, digital art"
#             elif preset_enum is ImagePreset.PAINTING:
#                 negative_prompt = "photograph, photo, cgi, video footage, video game footage"
#         return f"{negative_prompt} {self._negative_prompt}"
#
#     @negative_prompt.setter
#     def negative_prompt(self, value):
#         self._negative_prompt = value
#
#     @property
#     def second_prompt(self):
#         second_prompt = self.generator_settings.get("second_prompt", "")
#         prompt = ""
#         if self.image_preset != "":
#             preset_enum = ImagePreset(self.image_preset)
#             if preset_enum is ImagePreset.ILLUSTRATION:
#                 prompt = "A beautiful illustration of a"
#             elif preset_enum is ImagePreset.PHOTOGRAPH:
#                 prompt = "A beautiful photograph of a"
#             elif preset_enum is ImagePreset.PAINTING:
#                 prompt = "A beautiful painting of a"
#         return f"{prompt} {second_prompt}"
#
#     @property
#     def second_negative_prompt(self):
#         second_negative_prompt = self.generator_settings.get("second_negative_prompt", "")
#         negative_prompt = ""
#         if self.image_preset != "":
#             preset_enum = ImagePreset(self.image_preset)
#             if preset_enum is ImagePreset.ILLUSTRATION:
#                 negative_prompt = "photograph, realistic, photo realistic, ultra realistic, cgi"
#             elif preset_enum is ImagePreset.PHOTOGRAPH:
#                 negative_prompt = "illustration, drawing, painting, digital art"
#             elif preset_enum is ImagePreset.PAINTING:
#                 negative_prompt = "illustration, drawing, photograph, photo, realistic, photo realistic, ultra realistic, cgi"
#         return f"{negative_prompt} {second_negative_prompt}"
#
#     def __init__(self, settings: dict):
#         generator_settings = settings["generator_settings"]
#         self.generator_settings = generator_settings
#
#         self._prompt = ""
#         self._negative_prompt = ""
#
#
#         self.prompt = generator_settings.get("prompt", STABLEDIFFUSION_GENERATOR_SETTINGS["prompt"])
#         self.negative_prompt = generator_settings.get("negative_prompt", STABLEDIFFUSION_GENERATOR_SETTINGS["negative_prompt"])
#         self.steps = generator_settings.get("steps", STABLEDIFFUSION_GENERATOR_SETTINGS["steps"])
#         self.ddim_eta = generator_settings.get("ddim_eta", STABLEDIFFUSION_GENERATOR_SETTINGS["ddim_eta"])
#         self.height = generator_settings.get("height", settings.working_height)
#         self.width = generator_settings.get("width", settings.working_width)
#         self.scale = generator_settings.get("scale", STABLEDIFFUSION_GENERATOR_SETTINGS["scale"]) / 100.0
#         self.seed = generator_settings.get("seed", STABLEDIFFUSION_GENERATOR_SETTINGS["seed"])
#         self.random_seed = generator_settings.get("random_seed", STABLEDIFFUSION_GENERATOR_SETTINGS["random_seed"])
#         self.model = generator_settings.get("model", STABLEDIFFUSION_GENERATOR_SETTINGS["model"])
#         self.scheduler = generator_settings.get("scheduler", STABLEDIFFUSION_GENERATOR_SETTINGS["scheduler"])
#         self.prompt_triggers = generator_settings.get("prompt_triggers", STABLEDIFFUSION_GENERATOR_SETTINGS["prompt_triggers"])
#         self.strength = generator_settings.get("strength", STABLEDIFFUSION_GENERATOR_SETTINGS["strength"]) / 100.0
#         self.n_samples = generator_settings.get("n_samples", STABLEDIFFUSION_GENERATOR_SETTINGS["n_samples"])
#         self.enable_controlnet = settings["controlnet_enabled"]
#         self.clip_skip = generator_settings.get("clip_skip", STABLEDIFFUSION_GENERATOR_SETTINGS["clip_skip"])
#         self.variation = generator_settings.get("variation", STABLEDIFFUSION_GENERATOR_SETTINGS["variation"])
#         self.use_prompt_builder = generator_settings.get("use_prompt_builder", STABLEDIFFUSION_GENERATOR_SETTINGS["use_prompt_builder"])
#         self.version = generator_settings.get("version", STABLEDIFFUSION_GENERATOR_SETTINGS["version"])
#         self.is_preset = generator_settings.get("is_preset", STABLEDIFFUSION_GENERATOR_SETTINGS["is_preset"])
#         self.input_image = generator_settings.get("input_image", STABLEDIFFUSION_GENERATOR_SETTINGS["input_image"])
#         self.generator_name = generator_settings.get("generator_name", DEFAULT_GENERATOR_SETTINGS["generator_name"])
#         self.controlnet_image_settings = ControlnetImageSettings()

class MemorySettings:
    def __init__(self, **data):
        self.use_last_channels = data.get("use_last_channels", DEFAULT_MEMORY_SETTINGS["use_last_channels"])
        self.use_attention_slicing = data.get("use_attention_slicing", DEFAULT_MEMORY_SETTINGS["use_attention_slicing"])
        self.use_tf32 = data.get("use_tf32", DEFAULT_MEMORY_SETTINGS["use_tf32"])
        self.use_enable_vae_slicing = data.get("use_enable_vae_slicing", DEFAULT_MEMORY_SETTINGS["use_enable_vae_slicing"])
        self.use_accelerated_transformers = data.get("use_accelerated_transformers", DEFAULT_MEMORY_SETTINGS["use_accelerated_transformers"])
        self.use_tiled_vae = data.get("use_tiled_vae", DEFAULT_MEMORY_SETTINGS["use_tiled_vae"])
        self.enable_model_cpu_offload = data.get("enable_model_cpu_offload", DEFAULT_MEMORY_SETTINGS["enable_model_cpu_offload"])
        self.use_enable_sequential_cpu_offload = data.get("use_enable_sequential_cpu_offload", DEFAULT_MEMORY_SETTINGS["use_enable_sequential_cpu_offload"])
        self.use_cudnn_benchmark = data.get("use_cudnn_benchmark", DEFAULT_MEMORY_SETTINGS["use_cudnn_benchmark"])
        self.use_torch_compile = data.get("use_torch_compile", DEFAULT_MEMORY_SETTINGS["use_torch_compile"])
        self.use_tome_sd = data.get("use_tome_sd", DEFAULT_MEMORY_SETTINGS["use_tome_sd"])
        self.tome_sd_ratio = data.get("tome_sd_ratio", DEFAULT_MEMORY_SETTINGS["tome_sd_ratio"])
        self.move_unused_model_to_cpu = data.get("move_unused_model_to_cpu", DEFAULT_MEMORY_SETTINGS["move_unused_model_to_cpu"])
        self.unload_unused_models = data.get("unload_unused_models", DEFAULT_MEMORY_SETTINGS["unload_unused_models"])


class SDRequest(
    QObject,
    MediatorMixin,
    SettingsMixin
):
    def __init__(self, *args, **kwargs):
        QObject.__init__(self)
        MediatorMixin.__init__(self)
        SettingsMixin.__init__(self)
        self.action_has_safety_checker = False
        self.active_rect = None
        self.parent = None
        self.prompt_embeds = None
        self.negative_prompt_embeds = None
        self.pooled_prompt_embeds = None
        self.negative_pooled_prompt_embeds = None
        self.input_image = None

    @property
    def drawing_pad_image(self):
        base_64_image = self.image_to_image_settings.image
        image = convert_base64_to_image(base_64_image)
        if image is not None:
            image = image.convert("RGB")
        return image

    @property
    def image(self):
        return self.drawing_pad_image

    @property
    def outpaint_image(self):
        base_64_image = self.outpaint_settings.image
        image = convert_base64_to_image(base_64_image)
        if image is not None:
            image = image.convert("RGB")
        return image

    @property
    def section(self):
        section = GeneratorSection.TXT2IMG
        if self.drawing_pad_image is not None:
            section = GeneratorSection.IMG2IMG
        if self.outpaint_image is not None and self.outpaint_settings.enabled:
            section = GeneratorSection.OUTPAINT
        return section.value

    @property
    def is_outpaint(self) -> bool:
        return self.section == GeneratorSection.OUTPAINT.value

    @property
    def is_txt2img(self) -> bool:
        return self.section == GeneratorSection.TXT2IMG.value

    @property
    def is_img2img(self):
        return self.section == GeneratorSection.IMG2IMG.value

    def initialize_prompt_embeds(
        self,
        prompt_embeds,
        negative_prompt_embeds,
        pooled_prompt_embeds=None,
        negative_pooled_prompt_embeds=None,
        args: dict = None
    ):
        self.prompt_embeds = prompt_embeds
        self.negative_prompt_embeds = negative_prompt_embeds
        self.pooled_prompt_embeds = pooled_prompt_embeds
        self.negative_pooled_prompt_embeds = negative_pooled_prompt_embeds
        args = self.load_prompt_embed_args(
            prompt_embeds,
            negative_prompt_embeds,
            pooled_prompt_embeds,
            negative_pooled_prompt_embeds,
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
        pooled_prompt_embeds=None,
        negative_pooled_prompt_embeds=None,
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
        self.latents = latents
        self.callback_steps: int = 1
        self.cross_attention_kwargs_scale = cross_attention_kwargs_scale
        self.controlnet_image = controlnet_image
        self.model_changed = model_changed
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
            pooled_prompt_embeds=pooled_prompt_embeds,
            negative_pooled_prompt_embeds=negative_pooled_prompt_embeds,
            generator_request_data=generator_request_data
        )

        self.input_image = None #kwargs["image"] if "image" in kwargs else None

        args = {
            "num_inference_steps": self.generator_settings.steps,
            "callback": callback,
        }

        args.update(kwargs)
        args["callback_steps"] = self.callback_steps
        args["clip_skip"] = self.generator_settings.clip_skip

        if self.is_img2img or self.is_outpaint:
            args["height"] = self.application_settings.working_height
            args["width"] = self.application_settings.working_width
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
        pooled_prompt_embeds=None,
        negative_pooled_prompt_embeds=None,
        generator_request_data=None,
    ) -> dict:
        self.active_rect = active_rect
        if self.active_rect is None:
            self.active_rect = QRect(
                self.active_grid_settings.pos_x,
                self.active_grid_settings.pos_y,
                self.application_settings.working_width,
                self.application_settings.working_height,
            )
            self.active_rect.translate(
                -self.canvas_settings.pos_x,
                -self.canvas_settings.pos_y
            )

        width = int(self.application_settings.working_width)
        height = int(self.application_settings.working_height)
        clip_skip = int(self.generator_settings.clip_skip)

        args = {
            "action": self.section,
            "outpaint_box_rect": self.active_rect,
            "width": width,
            "height": height,
            "clip_skip": clip_skip,
        }

        args = self.load_prompt_embed_args(
            prompt_embeds,
            negative_prompt_embeds,
            pooled_prompt_embeds,
            negative_pooled_prompt_embeds,
            args
        )

        extra_args = self.prepare_extra_args(generator_request_data)

        if self.application_settings.controlnet_enabled and controlnet_image:
            if self.is_txt2img:
                extra_args["image"] = controlnet_image
            else:
                extra_args["control_image"] = controlnet_image

        return {**args, **extra_args}

    def prepare_extra_args(self, generator_request_data):
        extra_args = {
        }
        width = int(self.application_settings.working_width)
        height = int(self.application_settings.working_height)

        image = None
        mask = None
        if generator_request_data is not None:
            if "image" in generator_request_data:
                image = generator_request_data["image"]
            if "mask" in generator_request_data:
                mask = generator_request_data["mask"]

        if image is None and not self.is_outpaint:
            base64image = self.drawing_pad_settings.image
            if base64image != "":
                image = convert_base64_to_image(base64image)
                if image is not None:
                    image = image.convert("RGB")

        if self.is_txt2img:
            extra_args.update({
                "width": width,
                "height": height,
            })
        if not self.application_settings.controlnet_enabled:
            if self.is_txt2img:
                extra_args.update({
                    "guidance_scale": self.generator_settings.scale / 100.0,
                })
            elif self.is_img2img:
                extra_args.update({
                    "strength": self.generator_settings.strength / 100.0,
                    "guidance_scale": self.generator_settings.scale / 100.0,
                })
        if self.is_outpaint:
            if image is None:
                base64image = self.canvas_settings.image
                if base64image != "":
                    image = convert_base64_to_image(base64image)
                    if image is not None:
                        image = image.convert("RGB")
                    else:
                        print("IMAGE IS NONE")
            if mask is None:
                base64image = self.canvas_settings.mask
                if base64image != "":
                    mask = convert_base64_to_image(base64image)
                    if mask is not None:
                        mask = mask.convert("RGB")
                    else:
                        print("MASK IMAGE IS NONE")
            extra_args.update({
                "width": self.application_settings.working_width,
                "height": self.application_settings.working_height,
            })

        if image is not None:
            extra_args["image"] = image

        if mask is not None:
            extra_args["mask_image"] = mask

        controlnet_image = self.controlnet_image
        if self.application_settings.controlnet_enabled and controlnet_image:
            controlnet_args = {
                "guess_mode": None,
                "control_guidance_start": 0.0,
                "control_guidance_end": 1.0,
                "strength": self.generator_settings.strength / 100.0,
                "guidance_scale": self.generator_settings.scale / 100.0,
                "controlnet_conditioning_scale": self.controlnet_settings.conditioning_scale / 100.0,
                "controlnet": [
                    self.generator_settings.controlnet_image_settings.controlnet
                ],
            }

            if self.is_txt2img:
                controlnet_args["image"] = controlnet_image
            else:
                controlnet_args["control_image"] = controlnet_image

            extra_args.update(controlnet_args)
        return extra_args

    def load_prompt_embed_args(
        self,
        prompt_embeds,
        negative_prompt_embeds,
        pooled_prompt_embeds,
        negative_pooled_prompt_embeds,
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

            if pooled_prompt_embeds is not None and negative_pooled_prompt_embeds is not None:
                args["pooled_prompt_embeds"] = pooled_prompt_embeds
                args["negative_pooled_prompt_embeds"] = negative_pooled_prompt_embeds

                if "prompt_2" in args:
                    del args["prompt_2"]
                if "negative_prompt_2" in args:
                    del args["negative_prompt_2"]

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
