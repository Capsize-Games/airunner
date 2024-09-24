import threading
import traceback
import torch
from PIL import Image
from PySide6.QtCore import Slot, QObject, Signal

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
    ModelType,
    HandlerState, WorkerType
)
from airunner.aihandler.mixins.compel_mixin import CompelMixin
from airunner.aihandler.mixins.embedding_mixin import EmbeddingMixin
from airunner.aihandler.mixins.lora_mixin import LoraMixin
from airunner.aihandler.mixins.memory_efficient_mixin import MemoryEfficientMixin
from airunner.aihandler.mixins.scheduler_mixin import SchedulerMixin
from airunner.exceptions import InterruptedException, PipeNotLoadedException
from airunner.windows.main.embedding_mixin import EmbeddingMixin as EmbeddingDataMixin
from airunner.windows.main.pipeline_mixin import PipelineMixin
from airunner.windows.main.ai_model_mixin import AIModelMixin
from airunner.utils.create_worker import create_worker
from airunner.utils.get_torch_device import get_torch_device

SKIP_RELOAD_CONSTS = (
    SDMode.FAST_GENERATE,
    SDMode.DRAWING,
)


class LoadImageGeneratorModelWorker(QObject):
    finished = Signal()
    error = Signal(str)

    def __init__(self, sd_handler):
        super().__init__()
        self.sd_handler = sd_handler

    @Slot()
    def run(self):
        try:
            self.sd_handler.load_image_generator_model()
        except Exception as e:
            self.error.emit(str(e))
        finally:
            self.finished.emit()

    def cancel_load_model(self):
        self.sd_handler.cancel_load()


class SDHandler(
    BaseHandler,
    LoraMixin,
    MemoryEfficientMixin,
    EmbeddingMixin,
    CompelMixin,
    SchedulerMixin,
    # Data Mixins
    EmbeddingDataMixin,
    PipelineMixin,
    AIModelMixin,
    ControlnetHandlerMixin,
    SafetyCheckerMixin,
    ModelMixin,
):
    model_type = ModelType.SD

    def  __init__(self, *args, **kwargs):
        self._sd_request = None
        self.__current_state = HandlerState.INITIALIZED
        super().__init__(*args, **kwargs)
        EmbeddingMixin.__init__(self)
        SafetyCheckerMixin.__init__(self)
        EmbeddingDataMixin.__init__(self)
        AIModelMixin.__init__(self)
        LoraMixin.__init__(self)
        CompelMixin.__init__(self)
        SchedulerMixin.__init__(self)
        MemoryEfficientMixin.__init__(self)
        ControlnetHandlerMixin.__init__(self)
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
        self.pipe = None
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
        self.latents_worker = create_worker(WorkerType.LatentsWorker)
        self._loading_thread = None

        self.register(SignalCode.SD_UNLOAD_SIGNAL, self.__on_unload_stablediffusion_signal)

    @property
    def current_state(self):
        return self.__current_state

    @current_state.setter
    def current_state(self, value):
        self.__current_state = value
        self.emit_signal(SignalCode.SD_STATE_CHANGED_SIGNAL, value)

    def __on_unload_stablediffusion_signal(self, __message):
        if self.__load_image_generator_model_task.isRunning():
            self.__load_image_generator_model_task.cancel_load_model()
            self.logger.info("Cancelled the image generator model loading task.")
        self.current_state = HandlerState.UNLOADED
        self.model_status = self.current_state

    @property
    def input_image(self):
        return self.sd_request.input_image

    @property
    def sd_request(self):
        if self._sd_request is None:
            self.sd_request = SDRequest()
        return self._sd_request

    @sd_request.setter
    def sd_request(self, value):
        self._sd_request = value

    def on_load_scheduler_signal(self):
        self.load_scheduler()

    def on_unload_scheduler_signal(self):
        self.unload_scheduler()

    def model_status_changed(self, message: dict):
        status = message["status"]
        self.model_status = status

    @property
    def is_pipe_loaded(self) -> bool:
        if self.sd_request.is_txt2img:
            return self.txt2img is not None
        elif self.sd_request.is_img2img:
            return self.img2img is not None
        elif self.sd_request.is_outpaint:
            return self.outpaint is not None

    @property
    def __cuda_error_message(self) -> str:
        return (
            f"VRAM too low for "
            f"{self.application_settings.working_width}x{self.application_settings.working_height} "
            f"resolution. Potential solutions: try again, use a different model, "
            f"restart the application, use a smaller size, upgrade your GPU."
        )

    @property
    def data_type(self):
        # if self.sd_request.memory_settings.use_enable_sequential_cpu_offload:
        #     return torch.float32
        # elif self.sd_request.memory_settings.enable_model_cpu_offload:
        #     return torch.float16
        # data_type = torch.float16 if self.cuda_is_available else torch.float
        # return data_type
        return torch.float16

    @property
    def inpaint_vae_model(self):
        try:
            return self.models_by_pipeline_action("inpaint_vae")[0]
        except IndexError:
            return None

    def load_stable_diffusion(self):
        if self._loading_thread is not None:
            self._loading_thread.join()
        self._loading_thread = threading.Thread(target=self.__load_stable_diffusion)
        self._loading_thread.start()

    def __load_stable_diffusion(self):
        self.logger.info("Loading stable diffusion")
        if self.application_settings.nsfw_filter:
            self.load_safety_checker()

        if self.application_settings.controlnet_enabled:
            self.emit_signal(SignalCode.CONTROLNET_LOAD_SIGNAL)

        if not self.scheduler:
            self.load_scheduler()
        self.load_image_generator_model()

    def interrupt_image_generation_signal(self):
        if self.current_state == HandlerState.GENERATING:
            self.do_interrupt_image_generation = True

    @property
    def device(self):
        return get_torch_device(self.memory_settings.default_gpu_sd)

    @property
    def do_load(self):
        return (
            self.sd_mode not in SKIP_RELOAD_CONSTS or
            not self.initialized
        )

    @property
    def cuda_is_available(self) -> bool:
        if self.memory_settings.enable_model_cpu_offload:
            return False
        return torch.cuda.is_available()

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
        if self.current_state not in (
            HandlerState.GENERATING,
            HandlerState.PREPARING_TO_GENERATE
        ):
            self.current_state = HandlerState.PREPARING_TO_GENERATE

            self.do_generate = True
            self.generator_request_data = message

            try:
                self.__run(message)
            except InterruptedException:
                pass
            except Exception as e:
                self.log_error(e, "Failed to generate")
            self.current_state = HandlerState.READY

    def __run(self, message: dict):
        try:
            response = self.generate(
                self.generator_settings,
                message
            )
        except PipeNotLoadedException as e:
            self.logger.warning(e)
            response = None

        if response:
            response["action"] = self.sd_request.section
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
            self.sd_request.section in ("outpaint",)
        ):
            message = f"This model does not support {self.sd_request.section}"
        traceback.print_exc()
        self.logger.error(error)
        self.emit_signal(SignalCode.LOG_ERROR_SIGNAL, message)
