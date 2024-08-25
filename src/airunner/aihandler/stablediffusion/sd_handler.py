import threading
import traceback
import torch
from PIL import Image
from airunner.aihandler.base_handler import BaseHandler
from airunner.aihandler.mixins.controlnet_mixin import ControlnetHandlerMixin
from airunner.aihandler.mixins.model_mixin import ModelMixin
from airunner.aihandler.mixins.safety_checker_mixin import SafetyCheckerMixin
from airunner.aihandler.stablediffusion.sd_request import SDRequest
from airunner.enums import (
    FilterType,
    HandlerType,
    SignalCode,
    SDMode,
    EngineResponseCode,
    ModelStatus,
    ModelType, HandlerState
)
from airunner.aihandler.mixins.compel_mixin import CompelMixin
from airunner.aihandler.mixins.embedding_mixin import EmbeddingMixin
from airunner.aihandler.mixins.lora_mixin import LoraMixin
from airunner.aihandler.mixins.memory_efficient_mixin import MemoryEfficientMixin
from airunner.aihandler.mixins.merge_mixin import MergeMixin
from airunner.aihandler.mixins.scheduler_mixin import SchedulerMixin
from airunner.exceptions import InterruptedException, PipeNotLoadedException
from airunner.windows.main.controlnet_model_mixin import ControlnetModelMixin
from airunner.windows.main.lora_mixin import LoraMixin as LoraDataMixin
from airunner.windows.main.embedding_mixin import EmbeddingMixin as EmbeddingDataMixin
from airunner.windows.main.pipeline_mixin import PipelineMixin
from airunner.windows.main.ai_model_mixin import AIModelMixin
from airunner.utils.create_worker import create_worker
from airunner.utils.get_torch_device import get_torch_device
from airunner.workers.latents_worker import LatentsWorker

SKIP_RELOAD_CONSTS = (
    SDMode.FAST_GENERATE,
    SDMode.DRAWING,
)


class SDHandler(
    BaseHandler,
    MergeMixin,
    LoraMixin,
    MemoryEfficientMixin,
    EmbeddingMixin,
    CompelMixin,
    SchedulerMixin,
    # Data Mixins
    LoraDataMixin,
    EmbeddingDataMixin,
    PipelineMixin,
    ControlnetModelMixin,
    AIModelMixin,
    ControlnetHandlerMixin,
    SafetyCheckerMixin,
    ModelMixin,
):
    def  __init__(self, *args, **kwargs):
        self._sd_request = None

        super().__init__(*args, **kwargs)
        LoraDataMixin.__init__(self)
        EmbeddingDataMixin.__init__(self)
        ControlnetModelMixin.__init__(self)
        AIModelMixin.__init__(self)
        LoraMixin.__init__(self)
        CompelMixin.__init__(self)
        SchedulerMixin.__init__(self)
        MemoryEfficientMixin.__init__(self)
        ControlnetHandlerMixin.__init__(self)
        SafetyCheckerMixin.__init__(self)
        ModelMixin.__init__(self)
        PipelineMixin.__init__(self)
        self.logger.debug("Loading Stable Diffusion model runner...")
        self.handler_type = HandlerType.DIFFUSER
        self._previous_model = ""
        self.safety_checker_status = ModelStatus.UNLOADED
        self.cross_attention_kwargs_scale: float = 1.0
        self._initialized = False
        self._reload_model = False
        self.current_model_branch = None
        self.state = None
        self.lora_loaded = False
        self.loaded_lora = []
        self._settings = None
        self._action = None
        self.embeds_loaded = False
        self._compel_proc = None
        self.current_prompt = None
        self.current_negative_prompt = None
        self._model = None
        self.requested_data = None
        self.generator_request_data = None
        self._allow_online_mode = None
        self.processor = None
        self.attempt_download = False
        self.latents_set = False
        self._latents = None
        self._safety_checker = None
        self.current_model = ""
        self.seed = 42
        self.use_prompt_converter = True
        self.depth_map = None
        self.model_data = None
        self.model_version = ""
        self.use_tiled_vae = False
        self.use_accelerated_transformers = False
        self.use_torch_compile = False
        self.is_sd_xl = False
        self.is_sd_xl_turbo = False
        self.is_turbo = False
        self.filters = None
        self.original_model_data = None
        self.denoise_strength = None
        self.face_enhance = False
        self.allow_online_mode = False
        self.extra_args = None
        self.latents = None
        self.sd_mode = None
        self.image_preset = ""
        self.data = {
            "action": "txt2img",
        }

        self.sd_mode = SDMode.DRAWING
        self.loaded = False
        self.loading = False
        self.sd_request.parent = self
        self.do_generate = False
        self._generator = None
        self.do_interrupt_image_generation = False
        self.latents_worker = create_worker(LatentsWorker)

        self.current_state = HandlerState.INITIALIZED

        self.model_status = {}
        for model_type in ModelType:
            self.model_status[model_type] = ModelStatus.UNLOADED

    @property
    def sd_request(self):
        if self._sd_request is None:
            self.sd_request = SDRequest()
        return self._sd_request

    @sd_request.setter
    def sd_request(self, value):
        self._sd_request = value

    def on_load_scheduler_signal(self, _message: dict):
        self.load_scheduler()

    def on_unload_scheduler_signal(self, _message: dict):
        self.unload_scheduler()

    def model_status_changed(self, message: dict):
        model = message["model"]
        status = message["status"]
        self.model_status[model] = status

    @property
    def is_pipe_loaded(self) -> bool:
        if self.sd_request.is_txt2img:
            return self.txt2img is not None
        elif self.sd_request.is_img2img:
            return self.img2img is not None
        elif self.sd_request.is_pix2pix:
            return self.pix2pix is not None
        elif self.sd_request.is_outpaint:
            return self.outpaint is not None
        elif self.sd_request.is_depth2img:
            return self.depth2img is not None

    @property
    def pipe(self):
        try:
            if self.sd_request.is_txt2img:
                return self.txt2img
            elif self.sd_request.is_img2img:
                return self.img2img
            elif self.sd_request.is_outpaint:
                return self.outpaint
            elif self.sd_request.is_depth2img:
                return self.depth2img
            elif self.sd_request.is_pix2pix:
                return self.pix2pix
            else:
                self.logger.warning(
                    (
                        f"Invalid action"
                        f" for pipe {self.sd_request.generator_settings.section}"
                        " Unable to load image generator model."
                    )
                )
                return None
        except Exception as e:
            self.logger.error(f"Error getting pipe {e}")
            return None

    @pipe.setter
    def pipe(self, value):
        if self.sd_request.is_txt2img:
            self.txt2img = value
        elif self.sd_request.is_img2img:
            self.img2img = value
        elif self.sd_request.is_outpaint:
            self.outpaint = value
        elif self.sd_request.is_depth2img:
            self.depth2img = value
        elif self.sd_request.is_pix2pix:
            self.pix2pix = value

    @property
    def __cuda_error_message(self) -> str:
        return (
            f"VRAM too low for "
            f"{self.settings['working_width']}x{self.settings['working_height']} "
            f"resolution. Potential solutions: try again, use a different model, "
            f"restart the application, use a smaller size, upgrade your GPU."
        )

    @property
    def data_type(self):
        if self.sd_request.memory_settings.use_enable_sequential_cpu_offload:
            return torch.float32
        elif self.sd_request.memory_settings.enable_model_cpu_offload:
            return torch.float16
        data_type = torch.float16 if self.cuda_is_available else torch.float
        return data_type

    @property
    def inpaint_vae_model(self):
        try:
            return self.models_by_pipeline_action("inpaint_vae")[0]
        except IndexError:
            return None

    def load_stable_diffusion(self):
        self.logger.info("Loading stable diffusion")

        if self.settings["nsfw_filter"]:
            threading.Thread(target=self.load_nsfw_filter).start()

        if self.settings["controlnet_enabled"]:
            threading.Thread(target=self.load_controlnet).start()

        if self.settings["sd_enabled"]:
            if not self.scheduler:
                threading.Thread(target=self.load_scheduler).start()
            threading.Thread(target=self.load_stable_diffusion_model).start()

    def interrupt_image_generation_signal(self, _message: dict = None):
        if self.current_state == HandlerState.GENERATING:
            self.do_interrupt_image_generation = True

    @property
    def device(self):
        return get_torch_device(self.settings["memory_settings"]["default_gpu"]["sd"])

    @property
    def do_load(self):
        return (
            self.sd_mode not in SKIP_RELOAD_CONSTS or
            not self.initialized
        )

    @property
    def cuda_is_available(self) -> bool:
        if self.settings["memory_settings"]["enable_model_cpu_offload"]:
            return False
        return torch.cuda.is_available()

    @property
    def do_load_compel(self) -> bool:
        return self.pipe and (
            (
                self.use_compel and (
                    self.prompt_embeds is None or
                    self.negative_prompt_embeds is None
                )
            )
        )

    @staticmethod
    def apply_filters(image, filters):
        for image_filter in filters:
            filter_type = FilterType(image_filter["filter_name"])
            if filter_type is FilterType.PIXEL_ART:
                scale = 4
                colors = 24
                for option in image_filter["options"]:
                    option_name = option["name"]
                    val = option["value"]
                    if option_name == "scale":
                        scale = val
                    elif option_name == "colors":
                        colors = val
                width = image.width
                height = image.height
                image = image.quantize(colors)
                image = image.resize((int(width / scale), int(height / scale)), resample=Image.NEAREST)
                image = image.resize((width, height), resample=Image.NEAREST)
        return image

    def handle_generate_signal(self, message: dict):
        if self.current_state is not HandlerState.GENERATING:
            self.current_state = HandlerState.GENERATING

            self.do_generate = True
            self.generator_request_data = message

            try:
                self.__run(message)
            except InterruptedException:
                pass
            except Exception as e:
                self.log_error(e, "Failed to generate")
            self.current_state = HandlerState.READY

    def load_stable_diffusion_model(self):
        if not self.settings["sd_enabled"]:
            return

        self.load_image_generator_model()

        try:
            self.add_lora_to_pipe()
        except Exception as e:
            self.logger.error(f"Error adding lora to pipe: {e}")
            self.reload_model = True

        #controlnet_initialized = False

        # try:
        #     controlnet_initialized = not self.settings["controlnet_enabled"] or (
        #         self.controlnet is not None and
        #         self.pipe.controlnet is not None and
        #         self.processor is not None
        #     )
        # except AttributeError:
        #     pass

        if (
            self.pipe is not None and
            self.safety_checker_initialized is True# and
            #controlnet_initialized is True
        ):
            self.current_state = HandlerState.READY
        else:
            self.current_state = HandlerState.ERROR

    def __reload_prompts(self):
        if (
            self.settings["generator_settings"]["image_preset"] != self.image_preset
        ):
            self.image_preset = self.settings["generator_settings"]["image_preset"]

        self.latents = None
        self.latents_set = False

        if self.do_load_compel:
            self.clear_prompt_embeds()
            self.load_prompt_embeds(
                self.pipe,
                prompt=self.sd_request.generator_settings.prompt,
                negative_prompt=self.sd_request.generator_settings.negative_prompt
            )
            self.data = self.sd_request.initialize_prompt_embeds(
                prompt_embeds=self.prompt_embeds,
                negative_prompt_embeds=self.negative_prompt_embeds,
                args=self.data
            )

        if "prompt" in self.data and "prompt_embeds" in self.data:
            del self.data["prompt"]

        if "negative_prompt" in self.data and "negative_prompt_embeds" in self.data:
            del self.data["negative_prompt"]

    def __run(self, message: dict):
        self.__reload_prompts()
        try:
            response = self.generate(
                self.settings,
                message
            )
        except PipeNotLoadedException as e:
            self.logger.warning(e)
            response = None

        if response:
            response["action"] = self.sd_request.generator_settings.section
            response["outpaint_box_rect"] = self.sd_request.active_rect

        self.emit_signal(SignalCode.ENGINE_RESPONSE_WORKER_RESPONSE_SIGNAL, {
            'code': EngineResponseCode.IMAGE_GENERATED,
            'message': response
        })

    def _final_callback(self):
        self.emit_signal(SignalCode.SD_PROGRESS_SIGNAL, {
            "step": self.sd_request.generator_settings.steps,
            "total": self.sd_request.generator_settings.steps,
        })
        self.latents_set = True

    def log_error(self, error, message=None):
        if message:
            self.logger.error(message)
        self.logger.error(error)
        traceback.print_exc()
        self._final_callback()

    def error_handler(self, error):
        message = str(error)
        if (
            "got an unexpected keyword argument 'image'" in message and
            self.sd_request.generator_settings.section in ["outpaint", "pix2pix", "depth2img"]
        ):
            message = f"This model does not support {self.sd_request.generator_settings.section}"
        traceback.print_exc()
        self.logger.error(error)
        self.emit_signal(SignalCode.LOG_ERROR_SIGNAL, message)
