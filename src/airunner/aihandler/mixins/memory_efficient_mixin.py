import torch
from dataclasses import dataclass
import tomesd

from airunner.utils.clear_memory import clear_memory


class MemoryEfficientMixin:
    def __init__(self):
        self.settings_flags = {
            'torch_compile_applied': False,
            'last_channels_applied': None,
            'vae_slicing_applied': None,
            'attention_slicing_applied': None,
            'tiled_vae_applied': None,
            'accelerated_transformers_applied': None,
            'cpu_offload_applied': None,
            'model_cpu_offload_applied': None,
            'tome_sd_applied': None,
            'tome_ratio': 0.0,
            'use_enable_sequential_cpu_offload': None,
            'enable_model_cpu_offload': None,
            'use_tome_sd': None,
        }
        torch.backends.cuda.matmul.allow_tf32 = self.settings["memory_settings"]["use_tf32"]

    @property
    def do_remove_tome_sd(self):
        return not self.settings["memory_settings"]["use_tome_sd"] and self.settings_flags['tome_sd_applied']

    def make_stable_diffusion_memory_efficient(self):
        if not self.pipe:
            self.logger.debug("Pipe is None, skipping memory efficient settings")
            return
        self.__apply_all_memory_settings()
        self.__move_stable_diffusion_to_cuda()

    def make_controlnet_memory_efficient(self):
        self.__move_controlnet_to_cuda()

    def reset_applied_memory_settings(self):
        for key in self.settings_flags:
            if key.endswith("_applied"):
                self.settings_flags[key] = None

    def move_pipe_to_cpu(self):
        self.__move_pipe_to_cpu()

    def __apply_all_memory_settings(self):
        self.__apply_setting("last_channels_applied", self.__apply_last_channels)
        self.__apply_setting("vae_slicing_applied", self.__apply_vae_slicing)
        self.__apply_setting("attention_slicing_applied", self.__apply_attention_slicing)
        self.__apply_setting("tiled_vae_applied", self.__apply_tiled_vae)
        self.__apply_setting("accelerated_transformers_applied", self.__apply_accelerated_transformers)
        self.__apply_setting("cpu_offload_applied", self.__apply_cpu_offload)
        self.__apply_setting("model_cpu_offload_applied", self.__apply_model_offload)
        self.__apply_setting("tome_sd_applied", self.__apply_tome)

    def __apply_setting(self, setting_name, apply_func):
        if self.settings_flags[setting_name] != self.settings["memory_settings"].get(setting_name):
            apply_func()
            self.settings_flags[setting_name] = self.settings["memory_settings"].get(setting_name)

    def __apply_last_channels(self):
        use_last_channels = self.settings["memory_settings"]["use_last_channels"]
        self.logger.debug(f"{'Enabling' if use_last_channels else 'Disabling'} torch.channels_last")
        self.pipe.unet.to(memory_format=torch.channels_last if use_last_channels else torch.contiguous_format)

    def __apply_vae_slicing(self):
        use_vae_slicing = self.settings["memory_settings"]["use_enable_vae_slicing"]
        if self.sd_request.section not in ["img2img", "outpaint", "controlnet"]:
            try:
                self.logger.debug(f"{'Enabling' if use_vae_slicing else 'Disabling'} vae slicing")
                if use_vae_slicing:
                    self.pipe.enable_vae_slicing()
                else:
                    self.pipe.disable_vae_slicing()
            except AttributeError:
                pass

    def __apply_attention_slicing(self):
        use_attention_slicing = self.settings["memory_settings"]["use_attention_slicing"]
        try:
            self.logger.debug(f"{'Enabling' if use_attention_slicing else 'Disabling'} attention slicing")
            if use_attention_slicing:
                self.pipe.enable_attention_slicing(1)
            else:
                self.pipe.disable_attention_slicing()
        except AttributeError as e:
            self.logger.warning(f"Failed to apply attention slicing: {e}")

    def __apply_tiled_vae(self):
        use_tiled_vae = self.settings["memory_settings"]["use_tiled_vae"]
        self.logger.debug(f"{'Applying' if use_tiled_vae else 'Not applying'} tiled vae")
        try:
            if use_tiled_vae:
                self.pipe.vae.enable_tiling()
        except AttributeError:
            self.logger.warning("Tiled vae not supported for this model")

    def __apply_accelerated_transformers(self):
        use_accelerated_transformers = self.settings["memory_settings"]["use_accelerated_transformers"]
        from diffusers.models.attention_processor import AttnProcessor, AttnProcessor2_0
        self.logger.debug(f"{'Enabling' if use_accelerated_transformers else 'Disabling'} accelerated transformers")
        self.pipe.unet.set_attn_processor(AttnProcessor2_0() if use_accelerated_transformers else AttnProcessor())

    def __apply_cpu_offload(self):
        use_enable_sequential_cpu_offload = self.settings["memory_settings"]["use_enable_sequential_cpu_offload"]
        enable_model_cpu_offload = self.settings["memory_settings"]["enable_model_cpu_offload"]
        self.logger.debug(f"{'Enabling' if use_enable_sequential_cpu_offload else 'Disabling'} sequential cpu offload")
        if use_enable_sequential_cpu_offload and not enable_model_cpu_offload:
            self.__move_stable_diffusion_to_cpu()
            try:
                self.pipe.enable_sequential_cpu_offload()
            except NotImplementedError as e:
                self.logger.warning(f"Error applying sequential cpu offload: {e}")
                self.__move_stable_diffusion_to_cuda()

    def __apply_model_offload(self):
        enable_model_cpu_offload = self.settings["memory_settings"]["enable_model_cpu_offload"]
        use_enable_sequential_cpu_offload = self.settings["memory_settings"]["use_enable_sequential_cpu_offload"]
        if enable_model_cpu_offload and not use_enable_sequential_cpu_offload:
            self.logger.debug("Enabling model cpu offload")
            self.__move_stable_diffusion_to_cpu()
            self.pipe.enable_model_cpu_offload()

    def __apply_tome(self):
        tome_sd_ratio = self.settings["memory_settings"]["tome_sd_ratio"] / 1000
        self.logger.debug(f"Applying ToMe SD weight merging with ratio {tome_sd_ratio}")
        if self.settings_flags['use_tome_sd']:
            self.__remove_tome_sd()
            self.__apply_tome_sd(tome_sd_ratio)
        else:
            self.__remove_tome_sd()

    def __remove_tome_sd(self):
        self.logger.debug("Removing ToMe SD weight merging")
        try:
            tomesd.remove_patch(self.pipe)
        except Exception as e:
            self.logger.error(f"Error removing ToMe SD weight merging: {e}")

    def __apply_tome_sd(self, tome_sd_ratio):
        try:
            tomesd.apply_patch(self.pipe, ratio=tome_sd_ratio)
        except Exception as e:
            self.logger.error(f"Error applying ToMe SD weight merging: {e}")

    def __move_stable_diffusion_to_cuda(self):
        self.__move_pipe_to_cuda()

    def __move_pipe_to_cuda(self):
        if not self.pipe:
            return
        if not str(self.pipe.device).startswith("cuda"):
            self.logger.debug(f"Moving pipe to cuda (currently {self.pipe.device})")
            clear_memory()
            try:
                self.pipe.to(self.device, self.data_type)
            except Exception as e:
                self.logger.error(f"Error moving to cuda: {e}")

    def __move_controlnet_to_cuda(self):
        if hasattr(self.pipe, "controlnet") and self.pipe.controlnet:
            try:
                if not str(self.pipe.controlnet.device).startswith("cuda"):
                    self.logger.debug(f"Moving controlnet to cuda (currently {self.pipe.controlnet.device})")
                    self.pipe.controlnet.half()
                    self.pipe.controlnet.to(self.device)
            except Exception as e:
                self.logger.error(f"Error moving controlnet to cuda: {e}")
