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
from airunner.windows.main.lora_mixin import LoraMixin as LoraDataMixin
from airunner.windows.main.embedding_mixin import EmbeddingMixin as EmbeddingDataMixin
from airunner.windows.main.pipeline_mixin import PipelineMixin
from airunner.windows.main.controlnet_model_mixin import ControlnetModelMixin
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
        self.use_compel = False
        self.filters = None
        self.original_model_data = None
        self.denoise_strength = None
        self.face_enhance = False
        self.allow_online_mode = False
        self.extra_args = None
        self.latents = None
        self.sd_mode = None
        self.reload_prompts = False
        self.cur_prompt = ""
        self.cur_neg_prompt = ""
        self.data = {
            "action": "txt2img",
        }
        signals = {
            SignalCode.RESET_APPLIED_MEMORY_SETTINGS: self.on_reset_applied_memory_settings,
            SignalCode.SAFETY_CHECKER_UNLOAD_SIGNAL: self.unload_safety_checker,
            SignalCode.SAFETY_CHECKER_LOAD_SIGNAL: self.on_safety_checker_load_signal,
            SignalCode.SD_CANCEL_SIGNAL: self.on_sd_cancel_signal,
            SignalCode.SD_UNLOAD_SIGNAL: self.on_unload_stablediffusion_signal,
            SignalCode.SD_LOAD_SIGNAL: self.on_load_stablediffusion_signal,
            SignalCode.SCHEDULER_LOAD_SIGNAL: self.on_load_scheduler_signal,
            SignalCode.SCHEDULER_UNLOAD_SIGNAL: self.on_unload_scheduler_signal,
            SignalCode.SD_MOVE_TO_CPU_SIGNAL: self.on_move_to_cpu,
            SignalCode.START_AUTO_IMAGE_GENERATION_SIGNAL: self.on_start_auto_image_generation_signal,
            SignalCode.STOP_AUTO_IMAGE_GENERATION_SIGNAL: self.on_stop_auto_image_generation_signal,
            SignalCode.DO_GENERATE_SIGNAL: self.on_do_generate_signal,
            SignalCode.INTERRUPT_IMAGE_GENERATION_SIGNAL: self.on_interrupt_image_generation_signal,
            SignalCode.CHANGE_SCHEDULER_SIGNAL: self.on_change_scheduler_signal,
            SignalCode.SAFETY_CHECKER_MODEL_LOAD_SIGNAL: self.on_safety_checker_model_load_signal,
            SignalCode.SAFETY_CHECKER_MODEL_UNLOAD_SIGNAL: self.on_safety_checker_model_unload_signal,
            SignalCode.FEATURE_EXTRACTOR_LOAD_SIGNAL: self.on_feature_extractor_load_signal,
            SignalCode.FEATURE_EXTRACTOR_UNLOAD_SIGNAL: self.on_feature_extractor_unload_signal,
            SignalCode.SD_VAE_LOAD_SIGNAL: self.on_sd_vae_load_signal,
            SignalCode.SD_VAE_UNLOAD_SIGNAL: self.on_sd_vae_unload_signal,
        }

        for code, handler in signals.items():
            self.register(code, handler)


        self.sd_mode = SDMode.DRAWING
        self.loaded = False
        self.loading = False
        self.sd_request = None
        self.sd_request = SDRequest(model_data=self.model)
        self.sd_request.parent = self
        self.do_generate = False
        self._generator = None
        self.do_interrupt_image_generation = False
        self.latents_worker = create_worker(LatentsWorker)

        self.current_state = HandlerState.INITIALIZED

        self.model_status = {}
        self.model_status[ModelType.SD] = ModelStatus.UNLOADED
        self.model_status[ModelType.TTS] = ModelStatus.UNLOADED
        self.model_status[ModelType.TTS_PROCESSOR] = ModelStatus.UNLOADED
        self.model_status[ModelType.TTS_FEATURE_EXTRACTOR] = ModelStatus.UNLOADED
        self.model_status[ModelType.TTS_VOCODER] = ModelStatus.UNLOADED
        self.model_status[ModelType.TTS_SPEAKER_EMBEDDINGS] = ModelStatus.UNLOADED
        self.model_status[ModelType.TTS_TOKENIZER] = ModelStatus.UNLOADED
        self.model_status[ModelType.STT] = ModelStatus.UNLOADED
        self.model_status[ModelType.STT_PROCESSOR] = ModelStatus.UNLOADED
        self.model_status[ModelType.STT_FEATURE_EXTRACTOR] = ModelStatus.UNLOADED
        self.model_status[ModelType.CONTROLNET] = ModelStatus.UNLOADED
        self.model_status[ModelType.CONTROLNET_PROCESSOR] = ModelStatus.UNLOADED
        self.model_status[ModelType.SAFETY_CHECKER] = ModelStatus.UNLOADED
        self.model_status[ModelType.FEATURE_EXTRACTOR] = ModelStatus.UNLOADED
        self.model_status[ModelType.SCHEDULER] = ModelStatus.UNLOADED
        self.register(SignalCode.MODEL_STATUS_CHANGED_SIGNAL, self.on_model_status_changed_signal)

        self.load_stable_diffusion()

    def on_sd_vae_load_signal(self, _data: dict):
        self._load_vae()

    def on_sd_vae_unload_signal(self, _data: dict):
        self._unload_vae()

    def on_load_scheduler_signal(self, _message: dict):
        self.load_scheduler()

    def on_unload_scheduler_signal(self, _message: dict):
        self.unload_scheduler()

    def on_reset_applied_memory_settings(self, _data: dict):
        self.reset_applied_memory_settings()

    def on_model_status_changed_signal(self, message: dict):
        model = message["model"]
        status = message["status"]
        self.model_status[model] = status

    def on_change_scheduler_signal(self, data: dict):
        self.load_scheduler(force_scheduler_name=data["scheduler"])

    def on_safety_checker_model_load_signal(self, data_: dict):
        self._load_safety_checker_model()

    def on_safety_checker_model_unload_signal(self, data_: dict):
        self._unload_safety_checker_model()

    def on_feature_extractor_load_signal(self, data_: dict):
        self._load_feature_extractor_model()

    def on_feature_extractor_unload_signal(self, data_: dict):
        self._unload_feature_extractor_model()

    @property
    def model_path(self):
        if self.model is not None:
            return self.model["path"]

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
    def use_safety_checker(self):
        return self.settings["nsfw_filter"]

    @property
    def model(self):
        path = self.settings["generator_settings"]["model"]
        if path == "":
            name = self.settings["generator_settings"]["model_name"]
            model = self.ai_model_by_name(name)
        else:
            model = self.ai_model_by_path(path)
        return model

    @property
    def inpaint_vae_model(self):
        try:
            return self.models_by_pipeline_action("inpaint_vae")[0]
        except IndexError:
            return None

    def on_unload_stablediffusion_signal(self, _message: dict = None):
        self.unload_image_generator_model()

    def on_load_stablediffusion_signal(self, _message: dict = None):
        self.load_stable_diffusion_model()

    def on_load_stablediffusion_vae_signal(self, _message: dict = None):
        self._load_vae()

    def load_stable_diffusion(self):
        self.logger.info("Loading stable diffusion")

        if self.settings["nsfw_filter"]:
            self.load_safety_checker()

        if self.settings["controlnet_enabled"]:
            self.load_controlnet()

        if self.settings["sd_enabled"]:
            if not self.scheduler:
                self.load_scheduler()
            self.load_stable_diffusion_model()

    def load_stable_diffusion_model(self):
        self.load_image_generator_model()

        try:
            self.add_lora_to_pipe()
        except Exception as e:
            self.error_handler("Selected LoRA are not supported with this model")
            self.reload_model = True

        safety_checker_initialized = False
        controlnet_initialized = False

        try:
            safety_checker_initialized = not self.use_safety_checker or (
                self.safety_checker is not None and
                self.feature_extractor is not None and
                self.pipe.safety_checker is not None and
                self.pipe.feature_extractor is not None
            )
        except AttributeError:
            pass

        try:
            controlnet_initialized = not self.settings["controlnet_enabled"] or (
                self.controlnet is not None and
                self.pipe.controlnet is not None and
                self.processor is not None
            )
        except AttributeError:
            pass

        if (
            self.pipe is not None and
            safety_checker_initialized is True and
            controlnet_initialized is True
        ):
            self.current_state = HandlerState.READY
        else:
            self.current_state = HandlerState.ERROR

    def on_start_auto_image_generation_signal(self, _message: dict):
        # self.sd_mode = SDMode.DRAWING
        # self.generate()
        pass

    def on_sd_cancel_signal(self, _message: dict = None):
        print("on_sd_cancel_signal")

    def on_safety_checker_load_signal(self, _message: dict = None):
        self.load_safety_checker()

    def on_stop_auto_image_generation_signal(self, _message: dict = None):
        #self.sd_mode = SDMode.STANDARD
        pass

    def on_interrupt_image_generation_signal(self, _message: dict = None):
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

    def ai_model_by_name(self, name):
        try:
            return [model for model in self.settings["ai_models"] if model["name"] == name][0]
        except Exception as e:
            self.logger.error(f"Error finding model by name: {name}")

    def ai_model_by_path(self, path):
        try:
            return [model for model in self.settings["ai_models"] if model["path"] == path][0]
        except Exception as e:
            self.logger.error(f"Error finding model by path: {path}")

    @property
    def do_load_compel(self) -> bool:
        return self.pipe and (
            (
                self.use_compel and (self.prompt_embeds is None or self.negative_prompt_embeds is None)
            ) or
            self.reload_prompts
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

    def on_do_generate_signal(self, message: dict):
        if self.current_state is not HandlerState.GENERATING:
            self.current_state = HandlerState.GENERATING

            self.do_generate = True
            self.generator_request_data = message

            try:
                self.__run()
            except InterruptedException:
                pass
            except Exception as e:
                self.log_error(e, "Failed to generate")
            self.current_state = HandlerState.READY

    def __reload_prompts(self):
        if (
            self.settings["generator_settings"]["prompt"] != self.cur_prompt or
            self.settings["generator_settings"]["negative_prompt"] != self.cur_neg_prompt
        ):
            self.cur_prompt = self.settings["generator_settings"]["prompt"]
            self.cur_neg_prompt = self.settings["generator_settings"]["negative_prompt"]

            self.sd_request.generator_settings.parse_prompt(
                self.settings["nsfw_filter"],
                self.settings["generator_settings"]["prompt"],
                self.settings["generator_settings"]["negative_prompt"]
            )

            self.latents = None
            self.latents_set = False
            self.reload_prompts = True

        if self.do_load_compel:
            self.reload_prompts = False
            self.prompt_embeds = None
            self.negative_prompt_embeds = None
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

        # ensure only prompt OR prompt_embeds are used
        if "prompt" in self.data and "prompt_embeds" in self.data:
            del self.data["prompt"]

        if "negative_prompt" in self.data and "negative_prompt_embeds" in self.data:
            del self.data["negative_prompt"]

    def __run(self):
        self.__reload_prompts()
        try:
            response = self.generate(
                self.settings,
                self.sd_request,
                self.generator_request_data
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

    def on_move_to_cpu(self, message: dict = None):
        self.move_pipe_to_cpu()

    def send_error(self, message):
        self.emit_signal(SignalCode.LOG_ERROR_SIGNAL, message)

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
