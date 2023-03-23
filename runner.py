import os
import gc
import cv2
import numpy as np
import requests
from engine.base_runner import BaseRunner
from sdrunner.controlnet_utils import ade_palette
from qtvar import TQDMVar, ImageVar
import traceback
import torch
import io
from sdrunner.logger import logger
from PIL import Image
from controlnet_aux import HEDdetector, MLSDdetector, OpenposeDetector
os.environ["DISABLE_TELEMETRY"] = "1"
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"


def image_to_byte_array(image):
    img_byte_arr = io.BytesIO()
    image.save(img_byte_arr, format='PNG')
    img_byte_arr = img_byte_arr.getvalue()
    return img_byte_arr


class SDRunner(BaseRunner):
    _current_model: str = ""
    scheduler_name: str = "ddpm"
    do_nsfw_filter: bool = False
    initialized: bool = False
    seed: int = 42
    model_base_path: str = ""
    prompt: str = ""
    negative_prompt: str = ""
    guidance_scale: float = 7.5
    image_guidance_scale: float = 1.5
    num_inference_steps: int = 20
    height: int = 512
    width: int = 512
    C: int = 4
    f: int = 8
    batch_size = 1
    reload_model: bool = False
    action: str = ""
    options: dict = {}
    model = None
    do_cancel = False
    schedulers: dict = {
        "Euler": "EulerDiscreteScheduler",
        "Euler a": "EulerAncestralDiscreteScheduler",
        "LMS": "LMSDiscreteScheduler",
        "PNDM": "PNDMScheduler",
        "Heun": "HeunDiscreteScheduler",
        "DDIM": "DDIMScheduler",
        "DDPM": "DDPMScheduler",
        "DPM multistep": "DPMSolverMultistepScheduler",
        "DPM singlestep": "DPMSolverSinglestepScheduler",
        "DPM++ multistep": "DPMSolverMultistepScheduler",
        "DPM++ singlestep": "DPMSolverSinglestepScheduler",
        "DPM2 k": "KDPM2DiscreteScheduler",
        "DPM2 a k": "KDPM2AncestralDiscreteScheduler",
        "DEIS": "DEISMultistepScheduler",
    }
    registered_schedulers: dict = {}
    safety_checker = None
    current_model_branch = None
    txt2img = None
    img2img = None
    pix2pix = None
    outpaint = None
    depth2img = None
    controlnet = None
    superresolution = None
    state = None
    local_files_only = True

    # memory settings
    _use_last_channels = True
    _use_enable_sequential_cpu_offload = True
    _use_attention_slicing = True
    _use_tf32 = True
    _use_cudnn_benchmark = True
    _use_enable_vae_slicing = True
    _use_xformers = False
    _settings = None
    _action = None
    do_change_scheduler = False

    @property
    def do_mega_scale(self):
        return self.is_superresolution

    @property
    def action(self):
        return self._action

    @action.setter
    def action(self, value):
        self._action = value

    @property
    def action_has_safety_checker(self):
        return self.action not in ["depth2img", "superresolution"]

    @property
    def is_outpaint(self):
        return self.action == "outpaint"

    @property
    def is_txt2img(self):
        return self.action == "txt2img"

    @property
    def is_img2img(self):
        return self.action == "img2img"

    @property
    def is_controlnet(self):
        return self.action == "controlnet"

    @property
    def is_depth2img(self):
        return self.action == "depth2img"

    @property
    def is_pix2pix(self):
        return self.action == "pix2pix"

    @property
    def is_superresolution(self):
        return self.action == "superresolution"

    @property
    def current_model(self):
        return self._current_model

    @current_model.setter
    def current_model(self, model):
        if self._current_model != model:
            self._current_model = model
            if self.initialized:
                logger.info("SDRunner initialized")
                self._load_model()

    @property
    def model_path(self):
        return self.current_model

    @property
    def scheduler(self):
        if not self.model_path or self.model_path == "":
            # print stack trace
            import traceback
            traceback.print_stack()
            raise Exception("Chicken / egg problem, model path not set")

        if self.is_ckpt_model or self.is_safetensors:
            # skip scheduler for ckpt models
            return None
        import diffusers
        scheduler_class = getattr(diffusers, self.schedulers[self.scheduler_name])
        kwargs = {
            "subfolder": "scheduler"
        }
        # check if self.scheduler_name contains ++
        if self.scheduler_name.startswith("DPM"):
            kwargs["lower_order_final"] = self.num_inference_steps < 15
            if self.scheduler_name.find("++") != -1:
                kwargs["algorithm_type"] = "dpmsolver++"
            else:
                kwargs["algorithm_type"] = "dpmsolver"

        if self.current_model_branch:
            kwargs["variant"] = self.current_model_branch
        return scheduler_class.from_pretrained(
            self.model_path,
            local_files_only=self.local_files_only,
            use_auth_token=self.data["options"]["hf_token"],
            **kwargs
        )
        # else:
        #     raise ValueError("Invalid scheduler name")

    @property
    def cuda_error_message(self):
        if self.is_superresolution and self.scheduler_name == "DDIM":
            return f"Unable to run the model at {self.width}x{self.height} resolution using the DDIM scheduler. Try changing the scheduler to LMS or PNDM and try again."

        return f"You may not have enough GPU memory to run the model at {self.width}x{self.height} resolution. Potential solutions: try again, restart the application, use a smaller size, upgrade your GPU."
        # clear cache

    @property
    def is_pipe_loaded(self):
        if self.is_txt2img:
            return self.txt2img is not None
        elif self.is_img2img:
            return self.img2img is not None
        elif self.is_pix2pix:
            return self.pix2pix is not None
        elif self.is_outpaint:
            return self.outpaint is not None
        elif self.is_depth2img:
            return self.depth2img is not None
        elif self.is_superresolution:
            return self.superresolution is not None
        elif self.is_controlnet:
            return self.controlnet is not None

    @property
    def pipe(self):
        if self.is_txt2img:
            return self.txt2img
        elif self.is_img2img:
            return self.img2img
        elif self.is_outpaint:
            return self.outpaint
        elif self.is_depth2img:
            return self.depth2img
        elif self.is_pix2pix:
            return self.pix2pix
        elif self.is_superresolution:
            return self.superresolution
        elif self.is_controlnet:
            return self.controlnet
        else:
            raise ValueError(f"Invalid action {self.action} unable to get pipe")

    @pipe.setter
    def pipe(self, value):
        if self.is_txt2img:
            self.txt2img = value
        elif self.is_img2img:
            self.img2img = value
        elif self.is_outpaint:
            self.outpaint = value
        elif self.is_depth2img:
            self.depth2img = value
        elif self.is_pix2pix:
            self.pix2pix = value
        elif self.is_superresolution:
            self.superresolution = value
        elif self.is_controlnet:
            self.controlnet = value
        else:
            raise ValueError(f"Invalid action {self.action} unable to set pipe")

    @property
    def use_last_channels(self):
        return self._use_last_channels

    @use_last_channels.setter
    def use_last_channels(self, value):
        self._use_last_channels = value

    @property
    def use_enable_sequential_cpu_offload(self):
        return self._use_enable_sequential_cpu_offload

    @use_enable_sequential_cpu_offload.setter
    def use_enable_sequential_cpu_offload(self, value):
        self._use_enable_sequential_cpu_offload = value

    @property
    def use_attention_slicing(self):
        return self._use_attention_slicing

    @use_attention_slicing.setter
    def use_attention_slicing(self, value):
        self._use_attention_slicing = value

    @property
    def use_tf32(self):
        return self._use_tf32

    @use_tf32.setter
    def use_tf32(self, value):
        self._use_tf32 = value

    @property
    def use_cudnn_benchmark(self):
        return self._use_cudnn_benchmark

    @use_cudnn_benchmark.setter
    def use_cudnn_benchmark(self, value):
        self._use_cudnn_benchmark = value

    @property
    def enable_vae_slicing(self):
        return self._enable_vae_slicing

    @enable_vae_slicing.setter
    def enable_vae_slicing(self, value):
        self._enable_vae_slicing = value

    @property
    def cuda_is_available(self):
        return torch.cuda.is_available()

    @property
    def use_xformers(self):
        if not self.cuda_is_available:
            return False
        return self._use_xformers

    @use_xformers.setter
    def use_xformers(self, value):
        self._use_xformers = value

    @property
    def action_diffuser(self):
        from diffusers import (
            StableDiffusionPipeline,
            StableDiffusionImg2ImgPipeline,
            StableDiffusionInstructPix2PixPipeline,
            StableDiffusionInpaintPipeline,
            StableDiffusionDepth2ImgPipeline,
            StableDiffusionUpscalePipeline,
            StableDiffusionControlNetPipeline
        )

        if self.is_txt2img:
            return StableDiffusionPipeline
        elif self.is_img2img:
            return StableDiffusionImg2ImgPipeline
        elif self.is_pix2pix:
            return StableDiffusionInstructPix2PixPipeline
        elif self.is_outpaint:
            return StableDiffusionInpaintPipeline
        elif self.is_depth2img:
            return StableDiffusionDepth2ImgPipeline
        elif self.is_superresolution:
            return StableDiffusionUpscalePipeline
        elif self.is_controlnet:
            return StableDiffusionControlNetPipeline
        else:
            raise ValueError("Invalid action")

    @property
    def is_ckpt_model(self):
        return self._is_ckpt_file(self.model)

    @property
    def is_safetensors(self):
        return self._is_safetensor_file(self.model)

    @property
    def data_type(self):
        data_type = torch.half if self.cuda_is_available else torch.float
        return torch.float16 if self.use_xformers else data_type

    @property
    def device(self):
        return "cuda" if self.cuda_is_available else "cpu"

    def _clear_memory(self):
        torch.cuda.empty_cache()
        gc.collect()

    def move_models_to_cpu(self, skip_model):
        self.txt2img.to("cpu") if self.txt2img and skip_model != "txt2img" else None
        self.img2img.to("cpu") if self.img2img and skip_model != "img2img" else None
        self.pix2pix.to("cpu") if self.pix2pix and skip_model != "pix2pix" else None
        self.outpaint.to("cpu") if self.outpaint and skip_model != "outpaint" else None
        self.depth2img.to("cpu") if self.depth2img and skip_model != "depth2img" else None
        self.superresolution.to("cpu") if self.superresolution and skip_model != "superresolution" else None
        self.controlnet.to("cpu") if self.controlnet and skip_model != "controlnet" else None
        self._clear_memory()

    def load_controlnet_from_ckpt(self, pipeline):
        from diffusers import ControlNetModel, UniPCMultistepScheduler
        from diffusers import StableDiffusionControlNetPipeline
        controlnet = ControlNetModel.from_pretrained(
            self.controlnet_model,
            local_files_only=self.local_files_only,
            torch_dtype=self.data_type
        )
        pipeline.controlnet = controlnet
        pipeline = StableDiffusionControlNetPipeline(
            vae=pipeline.vae,
            text_encoder=pipeline.text_encoder,
            tokenizer=pipeline.tokenizer,
            unet=pipeline.unet,
            controlnet=controlnet,
            scheduler=pipeline.scheduler,
            safety_checker=pipeline.safety_checker,
            feature_extractor=pipeline.feature_extractor,
            requires_safety_checker=pipeline.requires_safety_checker
        )
        if self.data["options"]["enable_model_cpu_offload"]:
            pipeline.scheduler = UniPCMultistepScheduler.from_config(self.pipe.scheduler.config)
            pipeline.enable_model_cpu_offload()
        return pipeline

    controlnet_type = "canny"

    @property
    def controlnet_model(self):
        if self.controlnet_type == "canny":
            return "lllyasviel/sd-controlnet-canny"
        elif self.controlnet_type == "depth":
            return "fusing/stable-diffusion-v1-5-controlnet-depth"
        elif self.controlnet_type == "hed":
            return "fusing/stable-diffusion-v1-5-controlnet-hed"
        elif self.controlnet_type == "mlsd":
            return "fusing/stable-diffusion-v1-5-controlnet-mlsd"
        elif self.controlnet_type == "normal":
            return "fusing/stable-diffusion-v1-5-controlnet-normal"
        elif self.controlnet_type == "scribble":
            return "fusing/stable-diffusion-v1-5-controlnet-scribble"
        elif self.controlnet_type == "segmentation":
            return "fusing/stable-diffusion-v1-5-controlnet-seg"
        elif self.controlnet_type == "openpose":
            return "fusing/stable-diffusion-v1-5-controlnet-openpose"

    def load_controlnet(self):
        from diffusers import ControlNetModel
        return ControlNetModel.from_pretrained(
            self.controlnet_model,
            local_files_only=self.local_files_only,
            torch_dtype=self.data_type
        )

    def load_controlnet_scheduler(self):
        if self.data["options"]["enable_model_cpu_offload"]:
            from diffusers import UniPCMultistepScheduler
            self.pipe.scheduler = UniPCMultistepScheduler.from_config(self.pipe.scheduler.config)
            self.pipe.enable_model_cpu_offload()

    def _load_ckpt_model(self):
        schedulers = {
            "Euler": "euler",
            "Euler a": "euler-ancestral",
            "LMS": "lms",
            "PNDM": "pndm",
            "Heun": "heun",
            "DDIM": "ddim",
            "DDPM": "DDPMScheduler",
            "DPM multistep": "dpm",
            "DPM singlestep": "dpmss",
            "DPM++ multistep": "dpm++",
            "DPM++ singlestep": "dpmss++",
            "DPM2 k": "dpm2k",
            "DPM2 a k": "dpm2ak",
            "DEIS": "deis",
        }
        from diffusers.pipelines.stable_diffusion.convert_from_ckpt import \
            load_pipeline_from_original_stable_diffusion_ckpt
        logger.debug(f"Loading ckpt file, is safetensors {self.is_safetensors}")
        try:
            pipeline = load_pipeline_from_original_stable_diffusion_ckpt(
                checkpoint_path=self.model,
                scheduler_type=schedulers[self.scheduler_name],
                device=self.device,
                from_safetensors=self.is_safetensors
            )
            if self.is_controlnet:
                pipeline = self.load_controlnet_from_ckpt(pipeline)
        except Exception as e:
            print("Something went wrong loading the model file", e)
            self.set_message("Unable to load ckpt file", error=True)
            raise e
        # to half
        # determine which data type to move the model to
        pipeline.vae.to(self.data_type)
        pipeline.text_encoder.to(self.data_type)
        pipeline.unet.to(self.data_type)
        if self.do_nsfw_filter:
            pipeline.safety_checker.half()
        return pipeline

    def _load_model(self):
        logger.info("Loading model...")
        self.embeds_loaded = False
        if self.is_ckpt_model or self.is_safetensors:
            kwargs = {}
        else:
            kwargs = {
                "torch_dtype": self.data_type,
                "scheduler": self.scheduler,
                # "low_cpu_mem_usage": True, # default is already set to true
                "variant": self.current_model_branch
            }
            if self.current_model_branch:
                kwargs["variant"] = self.current_model_branch

        # move all models except for our current action to the CPU
        #self.move_models_to_cpu(skip_model=self.action)

        # special load case for img2img if txt2img is already loaded
        if self.is_img2img and self.txt2img is not None:
            self.img2img = self.action_diffuser(**self.txt2img.components)
        elif self.is_txt2img and self.img2img is not None:
            self.txt2img = self.action_diffuser(**self.img2img.components)
        elif self.pipe is None or self.reload_model:
            logger.debug("Loading model from scratch")
            if self.is_ckpt_model or self.is_safetensors:
                logger.debug("Loading ckpt or safetensors model")
                self.pipe = self._load_ckpt_model()
            else:
                logger.debug("Loading from diffusers pipeline")
                if self.is_controlnet:
                    kwargs["controlnet"] = self.load_controlnet()
                self.pipe = self.action_diffuser.from_pretrained(
                    self.model_path,
                    local_files_only=self.local_files_only,
                    use_auth_token=self.data["options"]["hf_token"],
                    **kwargs
                )
                if self.is_controlnet:
                    self.load_controlnet_scheduler()

            if hasattr(self.pipe, "safety_checker") and self.do_nsfw_filter:
                self.safety_checker = self.pipe.safety_checker

        # store the model_path
        self.pipe.model_path = self.model_path

        #self._load_embeddings()
        embeddings_folder = os.path.join(self.model_base_path, "embeddings")
        self.load_learned_embed_in_clip(embeddings_folder)

        self._apply_memory_efficient_settings()

    embeds_loaded = False
    def load_learned_embed_in_clip(self, learned_embeds_path):
        if self.embeds_loaded:
            return
        self.embeds_loaded = True
        if os.path.exists(learned_embeds_path):
            logger.info("Loading embeddings...")
            tokens = []
            for f in os.listdir(learned_embeds_path):
                try:

                    text_encoder = self.pipe.text_encoder
                    tokenizer = self.pipe.tokenizer
                    token = None

                    loaded_learned_embeds = torch.load(os.path.join(learned_embeds_path, f), map_location="cpu")

                    # separate token and the embeds
                    trained_token = list(loaded_learned_embeds.keys())[0]
                    if trained_token == "string_to_token":
                        trained_token = loaded_learned_embeds["name"]
                    embeds = loaded_learned_embeds[trained_token]
                    tokens.append(trained_token)

                    # cast to dtype of text_encoder
                    # dtype = text_encoder.get_input_embeddings().weight.dtype
                    # embeds.to(dtype)

                    # add the token in tokenizer
                    token = token if token is not None else trained_token
                    num_added_tokens = tokenizer.add_tokens(token)
                    if num_added_tokens == 0:
                        raise ValueError(
                            f"The tokenizer already contains the token {token}. Please pass a different `token` that is not already in the tokenizer.")

                    # resize the token embeddings
                    text_encoder.resize_token_embeddings(len(tokenizer))
                    # embeds.shape == [768], convert it to [1024]
                    #embeds = torch.cat([embeds, torch.zeros(256, dtype=embeds.dtype)], dim=0)

                    # get the id for the token and assign the embeds
                    token_id = tokenizer.convert_tokens_to_ids(token)

                    try:
                        text_encoder.get_input_embeddings().weight.data[token_id] = embeds
                    except Exception as e:
                        logger.warning(e)

                    self.pipe.text_encoder = text_encoder
                    self.pipe.tokenizer = tokenizer
                except Exception as e:
                    logger.warning(e)
            self.settings_manager.settings.available_embeddings.set(", ".join(tokens))

    def _load_embeddings(self):
        # in the embeddings foloder we will get all pt files and merge them into the model
        embeddings_folder = os.path.join(self.model_base_path, "embeddings")
        if os.path.exists(embeddings_folder):
            logger.info("Loading embeddings...")
            for f in os.listdir(embeddings_folder):
                if f.endswith(".pt"):
                    logger.debug(f"Loading {f}")
                    embedding = torch.load(os.path.join(embeddings_folder, f))
        else:
            print("No embeddings folder found", embeddings_folder)

    def _apply_memory_efficient_settings(self):
        logger.debug("Applying memory efficient settings")
        # enhance with memory settings
        if self.use_last_channels:
            logger.debug("Enabling torch.channels_last")
            self.pipe.unet.to(memory_format=torch.channels_last)
        else:
            logger.debug("Disabling torch.channels_last")
            self.pipe.unet.to(memory_format=torch.contiguous_format)

        if self.action not in ["img2img", "depth2img", "pix2pix", "outpaint", "superresolution", "controlnet"]:
            if self.use_enable_vae_slicing:
                logger.debug("Enabling vae slicing")
                self.pipe.enable_vae_slicing()
            else:
                logger.debug("Disabling vae slicing")
                self.pipe.disable_vae_slicing()

        if self.use_attention_slicing:
            logger.debug("Enabling attention slicing")
            self.pipe.enable_attention_slicing(slice_size="max")
        else:
            logger.debug("Disabling attention slicing")
            self.pipe.disable_attention_slicing()

        if self.use_xformers:
            from xformers.ops import MemoryEfficientAttentionFlashAttentionOp
            logger.debug("Enabling xformers")
            self.pipe.enable_xformers_memory_efficient_attention(
                attention_op=MemoryEfficientAttentionFlashAttentionOp)
            self.pipe.vae.enable_xformers_memory_efficient_attention(
                attention_op=None)
        else:
            logger.debug("Disabling xformers")
            self.pipe.disable_xformers_memory_efficient_attention()

    def _initialize(self):
        if not self.initialized or self.reload_model:
            logger.info("Initializing model")
            self._load_model()
            self.reload_model = False
            self.initialized = True

    def _is_ckpt_file(self, model):
        if not model:
            raise ValueError("ckpt path is empty")
        return model.endswith(".ckpt")

    def _is_safetensor_file(self, model):
        if not model:
            raise ValueError("safetensors path is empty")
        return model.endswith(".safetensors")

    def _do_reload_model(self):
        logger.info("Reloading model")
        if self.reload_model:
            self._load_model()

    def _prepare_model(self):
        logger.info("Prepare model")
        # get model and switch to it

        # get models from database
        model_name = self.options.get(f"{self.action}_model", None)

        self.set_message(f"Loading model {model_name}")

        if self._is_ckpt_file(model_name):
            self.current_model = model_name
        else:
            self.current_model = self.options.get(f"{self.action}_model_path", None)
            self.current_model_branch = self.options.get(f"{self.action}_model_branch", None)

    def _change_scheduler(self):
        if not self.do_change_scheduler:
            return
        if self.model_path and self.model_path != "":
            self.pipe.scheduler = self.scheduler
            self.do_change_scheduler = False
        else:
            logger.warning("Unable to change scheduler, model_path is not set")

    def _prepare_scheduler(self):
        scheduler_name = self.options.get(f"{self.action}_scheduler", "euler_a")
        if self.scheduler_name != scheduler_name:
            self.set_message(f"Preparing scheduler...")
            self.set_message("Loading scheduler")
            logger.info("Prepare scheduler")
            self.set_message("Preparing scheduler...")
            self.scheduler_name = scheduler_name
            if self.is_ckpt_model or self.is_safetensors:
                self.reload_model = True
            else:
                self.do_change_scheduler = True
        else:
            self.do_change_scheduler = False

    def _prepare_options(self, data):
        self.set_message(f"Preparing options...")
        try:
            action = data.get("action", "txt2img")
        except AttributeError:
            logger.error("No action provided")
            logger.error(data)
        options = data["options"]
        self.reload_model = False
        self.controlnet_type = self.options.get("controlnet", "canny")
        self.model_base_path = options["model_base_path"]
        model = options.get(f"{action}_model")
        if model != self.model:
            self.model = model
            self.reload_model = True
        controlnet_type = options.get(f"controlnet")
        if controlnet_type != self.controlnet_type:
            self.controlnet_type = controlnet_type
            self.reload_model = True
        self.prompt = options.get(f"{action}_prompt", self.prompt)
        self.negative_prompt = options.get(f"{action}_negative_prompt", self.negative_prompt)
        self.seed = int(options.get(f"{action}_seed", self.seed))
        self.guidance_scale = float(options.get(f"{action}_scale", self.guidance_scale))
        self.image_guidance_scale = float(options.get(f"{action}_image_scale", self.image_guidance_scale))
        self.strength = float(options.get(f"{action}_strength") or 1)
        self.num_inference_steps = int(options.get(f"{action}_steps", self.num_inference_steps))
        self.height = int(options.get(f"{action}_height", self.height))
        self.width = int(options.get(f"{action}_width", self.width))
        self.C = int(options.get(f"{action}_C", self.C))
        self.f = int(options.get(f"{action}_f", self.f))
        self.batch_size = int(options.get(f"{action}_n_samples", self.batch_size))
        do_nsfw_filter = bool(options.get(f"do_nsfw_filter", self.do_nsfw_filter))
        self.do_nsfw_filter = do_nsfw_filter
        self.action = action
        self.options = options

        # memory settings
        self.use_last_channels = options.get("use_last_channels", True) == True
        cpu_offload = options.get("use_enable_sequential_cpu_offload", True) == True
        if self.is_pipe_loaded and cpu_offload != self.use_enable_sequential_cpu_offload:
            logger.debug("Reloading model based on cpu offload")
            self.reload_model = True
        self.use_enable_sequential_cpu_offload = cpu_offload
        self.use_attention_slicing = options.get("use_attention_slicing", True) == True
        self.use_tf32 = options.get("use_tf32", True) == True
        self.use_cudnn_benchmark = options.get("use_cudnn_benchmark", True) == True
        self.use_enable_vae_slicing = options.get("use_enable_vae_slicing", True) == True
        use_xformers = options.get("use_xformers", True) == True
        if self.is_pipe_loaded  and use_xformers != self.use_xformers:
            logger.debug("Reloading model based on xformers")
            self.reload_model = True
        self.use_xformers = use_xformers
        # print logger.info of all memory settings in use
        logger.debug("Memory settings:")
        logger.debug(f"  use_last_channels: {self.use_last_channels}")
        logger.debug(f"  use_enable_sequential_cpu_offload: {self.use_enable_sequential_cpu_offload}")
        logger.debug(f"  use_attention_slicing: {self.use_attention_slicing}")
        logger.debug(f"  use_tf32: {self.use_tf32}")
        logger.debug(f"  use_cudnn_benchmark: {self.use_cudnn_benchmark}")
        logger.debug(f"  use_enable_vae_slicing: {self.use_enable_vae_slicing}")
        logger.debug(f"  use_xformers: {self.use_xformers}")

        torch.backends.cuda.matmul.allow_tf32 = self.use_tf32
        torch.backends.cudnn.benchmark = self.use_cudnn_benchmark

    def load_safety_checker(self, action):
        if not self.do_nsfw_filter:
            self.pipe.safety_checker = None
        else:
            self.pipe.safety_checker = self.safety_checker

    def do_sample(self, **kwargs):
        logger.info(f"Sampling {self.action}")
        self.set_message(f"Generating image...")
        # move everything but this action to the cpu
        # self.move_models_to_cpu(self.action)
        #if not self.is_ckpt_model and not self.is_safetensors:
        self.load_safety_checker(self.action)

        if not self.use_enable_sequential_cpu_offload:
            logger.debug("Moving to cuda")
            self.pipe.to("cuda") if self.cuda_is_available else None
        else:
            logger.debug("Enabling sequential cpu offload")
            self.pipe.enable_sequential_cpu_offload()
        try:
            if self.is_controlnet:
                #generator = torch.manual_seed(self.seed)
                kwargs["image"] = self._preprocess_for_controlnet(kwargs.get("image"), process_type=self.controlnet_type)
                #kwargs["generator"] = generator

            if self.is_controlnet:
                if kwargs.get("strength"):
                    kwargs["controlnet_conditioning_scale"] = kwargs["strength"]
                    del kwargs["strength"]

            output = self.pipe(
                self.prompt,
                negative_prompt=self.negative_prompt,
                guidance_scale=self.guidance_scale,
                num_inference_steps=self.num_inference_steps,
                num_images_per_prompt=1,
                callback=self.callback,
                **kwargs
            )
        except Exception as e:
            if "`flshattF` is not supported because" in str(e):
                # try again
                logger.info("Disabling xformers and trying again")
                self.pipe.enable_xformers_memory_efficient_attention(attention_op=None)
                self.pipe.vae.enable_xformers_memory_efficient_attention(attention_op=None)
                # redo the sample with xformers enabled
                return self.do_sample(**kwargs)
            output = None

        if output:
            image = output.images[0]

        nsfw_content_detected = None
        if self.action_has_safety_checker:
            nsfw_content_detected = output.nsfw_content_detected
        return image, nsfw_content_detected

    def _preprocess_canny(self, image):
        image = np.array(image)
        low_threshold = 100
        high_threshold = 200
        image = cv2.Canny(image, low_threshold, high_threshold)
        image = image[:, :, None]
        image = np.concatenate([image, image, image], axis=2)
        image = Image.fromarray(image)
        return image

    def _preprocess_depth(self, image):
        from transformers import pipeline
        depth_estimator = pipeline('depth-estimation')
        image = depth_estimator(image)['depth']
        image = np.array(image)
        image = image[:, :, None]
        image = np.concatenate([image, image, image], axis=2)
        image = Image.fromarray(image)
        return image

    def _preprocess_hed(self, image):
        hed = HEDdetector.from_pretrained('lllyasviel/ControlNet')
        image = hed(image)
        return image

    def _preprocess_mlsd(self, image):
        mlsd = MLSDdetector.from_pretrained('lllyasviel/ControlNet')
        image = mlsd(image)
        return image

    def _preprocess_normal(self, image):
        from transformers import pipeline
        depth_estimator = pipeline("depth-estimation", model="Intel/dpt-hybrid-midas")
        image = depth_estimator(image)['predicted_depth'][0]
        image = image.numpy()
        image_depth = image.copy()
        image_depth -= np.min(image_depth)
        image_depth /= np.max(image_depth)
        bg_threhold = 0.4
        x = cv2.Sobel(image, cv2.CV_32F, 1, 0, ksize=3)
        x[image_depth < bg_threhold] = 0
        y = cv2.Sobel(image, cv2.CV_32F, 0, 1, ksize=3)
        y[image_depth < bg_threhold] = 0
        z = np.ones_like(x) * np.pi * 2.0
        image = np.stack([x, y, z], axis=2)
        image /= np.sum(image ** 2.0, axis=2, keepdims=True) ** 0.5
        image = (image * 127.5 + 127.5).clip(0, 255).astype(np.uint8)
        image = Image.fromarray(image)
        return image

    def _preprocess_segmentation(self, image):
        from transformers import AutoImageProcessor, UperNetForSemanticSegmentation
        image_processor = AutoImageProcessor.from_pretrained("openmmlab/upernet-convnext-small")
        image_segmentor = UperNetForSemanticSegmentation.from_pretrained("openmmlab/upernet-convnext-small")
        pixel_values = image_processor(image, return_tensors="pt").pixel_values
        with torch.no_grad():
            outputs = image_segmentor(pixel_values)
        seg = image_processor.post_process_semantic_segmentation(outputs, target_sizes=[image.size[::-1]])[0]
        color_seg = np.zeros((seg.shape[0], seg.shape[1], 3), dtype=np.uint8)  # height, width, 3
        palette = np.array(ade_palette())
        for label, color in enumerate(palette):
            color_seg[seg == label, :] = color
        color_seg = color_seg.astype(np.uint8)
        image = Image.fromarray(color_seg)
        return image

    def _preprocess_openpose(self, image):
        openpose = OpenposeDetector.from_pretrained('lllyasviel/ControlNet')
        image = openpose(image)
        return image

    def _preprocess_scribble(self, image):
        hed = HEDdetector.from_pretrained('lllyasviel/ControlNet')
        image = hed(image, scribble=True)
        return image

    def _preprocess_for_controlnet(self, image, process_type="canny"):
        if process_type == "canny":
            image = self._preprocess_canny(image)
        elif process_type == "depth":
            image = self._preprocess_depth(image)
        elif process_type == "hed":
            image = self._preprocess_hed(image)
        elif process_type == "mlsd":
            image = self._preprocess_mlsd(image)
        elif process_type == "normal":
            image = self._preprocess_normal(image)
        elif process_type == "scribble":
            image = self._preprocess_scribble(image)
        elif process_type == "segmentation":
            image = self._preprocess_segmentation(image)
        elif process_type == "openpose":
            image = self._preprocess_openpose(image)
        return image

    def _sample_diffusers_model(self, data: dict):
        image = None
        nsfw_content_detected = None

        # disable warnings
        import warnings
        warnings.filterwarnings("ignore")
        from pytorch_lightning import seed_everything

        # disable info
        import logging
        logging.getLogger("lightning").setLevel(logging.WARNING)
        logging.getLogger("lightning_fabric.utilities.seed").setLevel(logging.WARNING)

        seed_everything(self.seed)
        action = self.action
        extra_args = {
        }

        if action == "txt2img":
            extra_args["width"] = self.width
            extra_args["height"] = self.height
        if action == "img2img":
            image = data["options"]["image"]
            extra_args["image"] = image
            extra_args["strength"] = self.strength
        elif action == "controlnet":
            image = data["options"]["image"]
            extra_args["image"] = image
            extra_args["strength"] = self.strength
        elif action == "pix2pix":
            image = data["options"]["image"]
            extra_args["image"] = image
            extra_args["image_guidance_scale"] = self.image_guidance_scale
        elif action == "depth2img":
            image = data["options"]["image"]
            # todo: get mask to work
            #mask_bytes = data["options"]["mask"]
            #mask = Image.frombytes("RGB", (self.width, self.height), mask_bytes)
            #extra_args["depth_map"] = mask
            extra_args["image"] = image
            extra_args["strength"] = self.strength
        elif self.is_superresolution:
            image = data["options"]["image"]
            if self.do_mega_scale:
                pass
            else:
                extra_args["image"] = image
        elif action == "outpaint":
            image = data["options"]["image"]
            mask = data["options"]["mask"]
            extra_args["image"] = image
            extra_args["mask_image"] = mask
            extra_args["width"] = self.width
            extra_args["height"] = self.height

        # do the sample
        try:
            if self.do_mega_scale:
                # first we will downscale the original image using the PIL algorithm
                # called "bicubic" which is a high quality algorithm
                # then we will upscale the image using the super resolution model
                # then we will upscale the image using the PIL algorithm called "bicubic"
                # to the desired size
                # the new dimensions of scaled_w and scaled_h should be the width and height
                # of the image that current image but aspect ratio scaled to 128
                # so if the image is 256x256 then the scaled_w and scaled_h should be 128x128 but
                # if the image is 512x256 then the scaled_w and scaled_h should be 128x64

                max_in_width = 512
                scale_size = 256
                in_width = self.width
                in_height = self.height
                original_image_width = data["options"]["original_image_width"]
                original_image_height = data["options"]["original_image_height"]

                if original_image_width > max_in_width:
                    scale_factor = max_in_width / original_image_width
                    in_width = int(original_image_width * scale_factor)
                    in_height = int(original_image_height * scale_factor)
                    scale_size = int(scale_size * scale_factor)

                if in_width > max_in_width:
                    # scale down in_width and in_height by scale_size
                    # but keep the aspect ratio
                    in_width = scale_size
                    in_height = int((scale_size / original_image_width) * original_image_height)

                # now we will scale the image to the new dimensions
                # and then upscale it using the super resolution model
                # and then downscale it using the PIL bicubic algorithm
                # to the original dimensions
                # this will give us a high quality image
                scaled_w = int(in_width * (scale_size / in_height))
                scaled_h = scale_size
                downscaled_image = image.resize((scaled_w, scaled_h), Image.BILINEAR)
                extra_args["image"] = downscaled_image
                upscaled_image, nsfw_content_detected = self.do_sample(**extra_args)
                # upscale back to self.width and self.height
                image = upscaled_image.resize((original_image_width, original_image_height), Image.BILINEAR)

                return image
            else:
                image, nsfw_content_detected = self.do_sample(**extra_args)
        except Exception as e:
            if "PYTORCH_CUDA_ALLOC_CONF" in str(e):
                raise Exception(self.cuda_error_message)
            elif "`flshattF` is not supported because" in str(e):
                # try again
                logger.info("Disabling xformers and trying again")
                self.pipe.enable_xformers_memory_efficient_attention(
                    attention_op=None)
                self.pipe.vae.enable_xformers_memory_efficient_attention(
                    attention_op=None)
                # redo the sample with xformers enabled
                return self._sample_diffusers_model(data)
            else:
                if self.is_dev_env:
                    traceback.print_exc()
                logger.error("Something went wrong while generating image")
                logger.error(e)

        self.final_callback()

        return image, nsfw_content_detected

    def _blend_images_by_average(self, composite, original):
        # upscale the original image
        upscaled_image = original.resize((self.width * 4, self.height * 4), Image.BICUBIC)

        # blend the two images together using average pixel value of the two images
        blended_image = Image.blend(composite, upscaled_image, 0.5)
        return blended_image

    def _blend_images_with_mask(self, composite, original, alpha_amount=0.5):
        """
        1. Take the original image and upscale it using "bicubic"
        2. Create a mask that is 0 for the new image and 1 for the original image
        3. Blend the original image with the new image using the mask
        """
        # upscale the original image
        upscaled_image = original.resize((self.width * 4, self.height * 4), Image.BICUBIC)

        # both images have no alpha channel, they are RGB images
        # so we need to add an alpha channel to the composite image
        # so we can blend it with the original image
        composite = composite.convert("RGBA")

        # create a mask based on alpha_amount, where alpha_amount == 0 means the new image is used and
        # alpha_amount == 1 means the original image is used
        mask = Image.new("L", composite.size, int(255 * alpha_amount))

        # paste the mask into the composite image
        composite.putalpha(mask)

        # blend the composite image with the original image
        blended_image = Image.composite(composite, upscaled_image, mask)

        return blended_image

    def _generate(self, data: dict, image_var: ImageVar = None):
        logger.info("_generate called")
        self._prepare_options(data)
        self._prepare_scheduler()
        self._prepare_model()
        self._initialize()
        self._change_scheduler()

        if not self.use_enable_sequential_cpu_offload:
            self.move_models_to_cpu(self.action)
            self._clear_memory()

        self._apply_memory_efficient_settings()
        for n in range(self.batch_size):
            image, nsfw_content_detected = self._sample_diffusers_model(data)
            self.image_handler(image, data, nsfw_content_detected)
            self.seed = self.seed + 1
            if self.do_cancel:
                self.do_cancel = False
                break

    def image_handler(self, image, data, nsfw_content_detected):
        if image:
            if self._image_handler:
                self._image_handler(image, data, nsfw_content_detected)
            elif self._image_var:
                self._image_var.set({
                    "image": image,
                    "data": data,
                    "nsfw_content_detected": nsfw_content_detected == True,
                })

    def final_callback(self):
        total = int(self.num_inference_steps * self.strength)
        self.tqdm_callback(total, total, self.action)

    def callback(self, step: int, _time_step, _latents):
        # convert _latents to image
        self.tqdm_callback(
            step,
            int(self.num_inference_steps * self.strength),
            self.action,
            image=self._latents_to_image(_latents),
            data=self.data,
        )
        pass

    def _latents_to_image(self, latents: torch.Tensor):
        # convert tensor to image
        #image = self.pipe.vae.decoder(latents)
        image = latents.permute(0, 2, 3, 1)
        image = image.detach().cpu().numpy()
        image = image[0]
        image = (image * 255).astype(np.uint8)
        image = Image.fromarray(image)
        return image

    @property
    def has_internet_connection(self):
        try:
            response = requests.get('https://huggingface.co/')
            return True
        except requests.ConnectionError:
            return False

    def generator_sample(
        self,
        data: dict,
        image_var: callable,
        error_var: callable = None
    ):
        # check if model in data is cached
        # if not, download it
        # if it is, load it
        self.data = data
        self.set_message("Generating image...")
        if data["action"] == "outpaint" and self.initialized and self.outpaint is None:
            self.initialized = False
        elif data["action"] == "img2img" and self.initialized and self.img2img is None:
            self.initialized = False
        elif data["action"] == "controlnet" and self.initialized and self.controlnet is None:
            self.initialized = False
        elif data["action"] == "depth" and self.initialized and self.depth2img is None:
            self.initialized = False
        elif data["action"] == "superresolution" and self.initialized and self.superresolution is None:
            self.initialized = False
        elif data["action"] == "txt2img" and self.initialized and self.txt2img is None:
            self.initialized = False
        error = None
        try:
            self._generate(data, image_var=image_var)
        except OSError as e:
            err = e.args[0]
            logger.error(err)
            error = "model_not_found"
            err_obj = e
            traceback.print_exc() if self.is_dev_env else logger.error(err_obj)
        except TypeError as e:
            error = f"TypeError during generation {self.action}"
            traceback.print_exc() if self.is_dev_env else logger.error(e)
        except Exception as e:
            if "PYTORCH_CUDA_ALLOC_CONF" in str(e):
                raise Exception(self.cuda_error_message)
            error = f"Error during generation"
            traceback.print_exc() if self.is_dev_env else logger.error(e)

        if error:
            self.initialized = False
            self.reload_model = True
            if error == "model_not_found" and self.local_files_only and self.has_internet_connection:
                # check if we have an internet connection
                self.set_message("Downloading model files...")
                self.local_files_only = False
                self._initialize()
                return self.generator_sample(data, image_var, error_var)
            elif not self.has_internet_connection:
                self.set_message("Please check your internet connection and try again.", error=True)
            self.scheduler_name = None
            self._current_model = None
            self.local_files_only = True

            # handle the error (sends to client)
            self.error_handler(error, error_var)

    def cancel(self):
        self.do_cancel = True
