import os
import torch
from aihandler.settings import LOG_LEVEL
from aihandler.logger import logger
import logging
logging.disable(LOG_LEVEL)
logger.set_level(logger.DEBUG)


class MemoryEfficientMixin:
    torch_compile_applied: bool = False

    @property
    def use_last_channels(self):
        return self.settings_manager.settings.use_last_channels.get() and not self.is_txt2vid

    @property
    def use_enable_sequential_cpu_offload(self):
        return self.settings_manager.settings.use_enable_sequential_cpu_offload.get()

    @property
    def use_attention_slicing(self):
        return self.settings_manager.settings.use_attention_slicing.get()

    @property
    def use_tf32(self):
        return self.settings_manager.settings.use_tf32.get()

    @property
    def enable_vae_slicing(self):
        return self.settings_manager.settings.use_enable_vae_slicing.get()

    @property
    def use_accelerated_transformers(self):
        return self.cuda_is_available and self.settings_manager.settings.use_accelerated_transformers.get()

    @property
    def use_torch_compile(self):
        return self.settings_manager.settings.use_torch_compile.get()

    @property
    def use_tiled_vae(self):
        return self.settings_manager.settings.use_tiled_vae.get()

    def apply_last_channels(self):
        if self.use_kandinsky or self.is_txt2vid or self.is_shapegif:
            return
        if self.use_last_channels:
            logger.info("Enabling torch.channels_last")
            self.pipe.unet.to(memory_format=torch.channels_last)
        else:
            logger.info("Disabling torch.channels_last")
            self.pipe.unet.to(memory_format=torch.contiguous_format)

    def apply_vae_slicing(self):
        if self.action not in [
            "img2img", "depth2img", "pix2pix", "outpaint", "superresolution", "controlnet", "upscale"
        ] and not self.use_kandinsky:
            if self.use_enable_vae_slicing or self.is_txt2vid:
                logger.info("Enabling vae slicing")
                try:
                    self.pipe.enable_vae_slicing()
                except AttributeError:
                    pass
            else:
                logger.info("Disabling vae slicing")
                try:
                    self.pipe.disable_vae_slicing()
                except AttributeError:
                    pass

    def apply_attention_slicing(self):
        if self.use_attention_slicing:
            logger.info("Enabling attention slicing")
            self.pipe.enable_attention_slicing(1)
        else:
            logger.info("Disabling attention slicing")
            self.pipe.disable_attention_slicing()

    def apply_tiled_vae(self):
        if self.use_tiled_vae:
            logger.info("Applying tiled vae")
            # from diffusers import UniPCMultistepScheduler
            # self.pipe.scheduler = UniPCMultistepScheduler.from_config(self.pipe.scheduler.config)
            try:
                self.pipe.vae.enable_tiling()
            except AttributeError:
                logger.warning("Tiled vae not supported for this model")

    def apply_accelerated_transformers(self):
        if self.use_kandinsky:
            return
        if not (self.cuda_is_available and self.settings_manager.settings.use_accelerated_transformers.get()):
            logger.info("Disabling accelerated transformers")
            self.pipe.unet.set_default_attn_processor()

    def save_unet(self, file_path, file_name):
        logger.info(f"Saving compiled torch model {file_name}")
        unet_file = os.path.join(file_path, file_name)
        if not os.path.exists(file_path):
            os.makedirs(file_path)
        torch.save(self.pipe.unet.state_dict(), unet_file)

    def load_unet(self, file_path, file_name):
        logger.info(f"Loading compiled torch model {file_name}")
        unet_file = os.path.join(file_path, file_name)
        self.pipe.unet.state_dict = torch.load(unet_file, map_location="cuda")

    def apply_torch_compile(self):
        """
        Torch compile has limited support
            - No support for Windows
            - Fails with the compiled version of AI Runner
        Because of this, we are disabling it until a better solution is found.

        if not self.use_torch_compile or self.torch_compile_applied:
            return
        unet_path = self.unet_model_path
        if unet_path is None or unet_path == "":
            unet_path = os.path.join(self.model_base_path, "compiled_unet")
        file_path = os.path.join(os.path.join(unet_path, self.model_path))
        model_name = self.options.get(f"{self.action}_model", None)
        file_name = f"{model_name}.pt"
        if os.path.exists(os.path.join(file_path, file_name)):
            self.load_unet(file_path, file_name)
            self.pipe.unet.to(memory_format=torch.channels_last)
        else:
            logger.info(f"Compiling torch model {model_name}")
            self.pipe.unet.to(memory_format=torch.channels_last)
            self.pipe.unet = torch.compile(self.pipe.unet)
            self.pipe(prompt=self.prompt)
            self.save_unet(file_path, file_name)
        self.torch_compile_applied = True
        """
        return

    def enable_memory_chunking(self):
        if self.is_txt2vid and not self.is_zeroshot:
            self.pipe.unet.enable_forward_chunking(chunk_size=1, dim=1)

    def move_pipe_to_cuda(self, pipe):
        if not self.use_enable_sequential_cpu_offload and not self.enable_model_cpu_offload:
            logger.info("Moving to cuda")
            pipe.to("cuda", torch.half) if self.cuda_is_available else None
        return pipe

    def move_pipe_to_cpu(self, pipe):
        logger.info("Moving to cpu")
        try:
            pipe.to("cpu", torch.float32)
        except NotImplementedError:
            logger.warning("Not implemented error when moving to cpu")
        return pipe

    def apply_cpu_offload(self):
        if self.use_enable_sequential_cpu_offload and not self.enable_model_cpu_offload:
            logger.info("Enabling sequential cpu offload")
            self.pipe = self.move_pipe_to_cpu(self.pipe)
            try:
                self.pipe.enable_sequential_cpu_offload()
            except NotImplementedError:
                logger.warning("Not implemented error when applying sequential cpu offload")
                self.pipe = self.move_pipe_to_cuda(self.pipe)

    def apply_model_offload(self):
        if self.enable_model_cpu_offload \
           and not self.use_enable_sequential_cpu_offload \
           and hasattr(self.pipe, "enable_model_cpu_offload"):
            logger.info("Enabling model cpu offload")
            self.pipe = self.move_pipe_to_cpu(self.pipe)
            self.pipe.enable_model_cpu_offload()

    def apply_memory_efficient_settings(self):
        logger.info("Applying memory efficient settings")
        self.apply_last_channels()
        self.enable_memory_chunking()
        self.apply_vae_slicing()
        self.apply_cpu_offload()
        self.apply_model_offload()
        self.pipe = self.move_pipe_to_cuda(self.pipe)
        self.apply_attention_slicing()
        self.apply_tiled_vae()
        self.apply_accelerated_transformers()
        self.apply_torch_compile()
