import os
import torch
import functools
from dataclasses import dataclass
from typing import Optional
import tomesd

from airunner.enums import SignalCode, ModelType, DeviceName
from airunner.utils.clear_memory import clear_memory


@dataclass
class UNet2DConditionOutput:
    sample: torch.FloatTensor


class TracedUNet(torch.nn.Module):
    def __init__(self, pipe):
        super().__init__()
        self.config = pipe.unet.config
        self.in_channels = pipe.unet.in_channels
        self.device = pipe.unet.device

    def forward(self, latent_model_input, t, encoder_hidden_states, **kwargs):
        unet_traced = torch.jit.load("unet_traced.pt")
        sample = unet_traced(latent_model_input, t, encoder_hidden_states)[0]
        return UNet2DConditionOutput(sample=sample)


class MemoryEfficientMixin:
    def __init__(self):
        """
        Apply memory efficient settings to the Stable Diffusion pipeline.
        """
        self.torch_compile_applied: bool = False
        self.last_channels_applied: bool = Optional[None]
        self.vae_slicing_applied: bool = Optional[None]
        self.attention_slicing_applied: bool = Optional[None]
        self.tiled_vae_applied: bool = Optional[None]
        self.accelerated_transformers_applied: bool = Optional[None]
        self.cpu_offload_applied: bool = Optional[None]
        self.model_cpu_offload_applied: bool = Optional[None]
        self.tome_sd_applied: bool = Optional[None]
        self.tome_ratio: float = Optional[None]
        self.use_enable_sequential_cpu_offload: bool = Optional[None]
        self.enable_model_cpu_offload: bool = Optional[None]
        self.use_tome_sd: bool = Optional[None]
        self.tome_sd_ratio = 0.0
        torch.backends.cuda.matmul.allow_tf32 = self.settings["memory_settings"]["use_tf32"]

    @property
    def do_remove_tome_sd(self):
        return not self.settings["memory_settings"]["use_tome_sd"] and self.tome_sd_applied

    def make_stable_diffusion_memory_efficient(self):
        if self.pipe is None:
            self.logger.debug("Pipe is None, skipping memory efficient settings")
            return
        self.__apply_last_channels()
        self.__enable_memory_chunking()
        self.__apply_vae_slicing()
        self.__apply_cpu_offload()
        self.__apply_model_offload()
        self.__move_stable_diffusion_to_cuda()
        self.__apply_attention_slicing()
        self.__apply_tiled_vae()
        self.__apply_accelerated_transformers()
        self.__apply_tome()

        # TODO
        #self.apply_torch_compile()
        #self.apply_torch_trace()

    def make_controlnet_memory_efficient(self):
        self.__move_controlnet_to_cuda()

    def reset_applied_memory_settings(self):
        self.last_channels_applied = None
        self.vae_slicing_applied = None
        self.attention_slicing_applied = None
        self.tiled_vae_applied = None
        self.accelerated_transformers_applied = None
        self.cpu_offload_applied = None
        self.model_cpu_offload_applied = None
        self.use_enable_sequential_cpu_offload = None
        self.enable_model_cpu_offload = None

    def move_pipe_to_cpu(self):
        self.__move_pipe_to_cpu()

    def __apply_last_channels(self):
        if self.last_channels_applied == self.settings["memory_settings"]["use_last_channels"]:
            return
        self.last_channels_applied = self.settings["memory_settings"]["use_last_channels"]
        if self.settings["memory_settings"]["use_last_channels"]:
            self.logger.debug("Enabling torch.channels_last")
            self.pipe.unet.to(memory_format=torch.channels_last)
        else:
            self.logger.debug("Disabling torch.channels_last")
            self.pipe.unet.to(memory_format=torch.contiguous_format)

    def __apply_vae_slicing(self):
        if self.vae_slicing_applied == self.settings["memory_settings"]["use_enable_vae_slicing"]:
            return
        self.vae_slicing_applied = self.settings["memory_settings"]["use_enable_vae_slicing"]

        if self.sd_request.generator_settings.section not in [
            "img2img", "depth2img", "pix2pix", "outpaint", "superresolution", "controlnet", "upscale"
        ]:
            if self.settings["memory_settings"]["use_enable_vae_slicing"]:
                self.logger.debug("Enabling vae slicing")
                try:
                    self.pipe.enable_vae_slicing()
                except AttributeError:
                    pass
            else:
                self.logger.debug("Disabling vae slicing")
                try:
                    self.pipe.disable_vae_slicing()
                except AttributeError:
                    pass

    def __apply_attention_slicing(self):
        if self.attention_slicing_applied == self.settings["memory_settings"]["use_attention_slicing"]:
            return
        self.attention_slicing_applied = self.settings["memory_settings"]["use_attention_slicing"]

        if self.settings["memory_settings"]["use_attention_slicing"]:
            self.logger.debug("Enabling attention slicing")
            self.pipe.enable_attention_slicing(1)
        else:
            self.logger.debug("Disabling attention slicing")
            self.pipe.disable_attention_slicing()

    def __apply_tiled_vae(self):
        if self.tiled_vae_applied == self.settings["memory_settings"]["use_tiled_vae"]:
            return
        self.tiled_vae_applied = self.settings["memory_settings"]["use_tiled_vae"]

        if self.settings["memory_settings"]["use_tiled_vae"]:
            self.logger.debug("Applying tiled vae")
            # from diffusers import UniPCMultistepScheduler
            # self.pipe.scheduler = UniPCMultistepScheduler.from_config(self.pipe.scheduler.config)
            try:
                self.pipe.vae.enable_tiling()
            except AttributeError:
                self.logger.warning("Tiled vae not supported for this model")

    def __apply_accelerated_transformers(self):
        if self.accelerated_transformers_applied == self.settings["memory_settings"]["use_accelerated_transformers"]:
            return
        self.accelerated_transformers_applied = self.settings["memory_settings"]["use_accelerated_transformers"]

        from diffusers.models.attention_processor import AttnProcessor, AttnProcessor2_0
        if not self.cuda_is_available or not self.settings["memory_settings"]["use_accelerated_transformers"]:
            self.logger.debug("Disabling accelerated transformers")
            self.pipe.unet.set_attn_processor(AttnProcessor())
        else:
            self.pipe.unet.set_attn_processor(AttnProcessor2_0())

    def __save_unet(self, file_path, file_name):
        self.logger.debug(f"Saving compiled torch model {file_name}")
        unet_file = os.path.join(file_path, file_name)
        if not os.path.exists(file_path):
            os.makedirs(file_path)
        torch.save(self.pipe.unet.state_dict(), unet_file)

    def __load_unet(self, file_path, file_name):
        self.logger.debug(f"Loading compiled torch model {file_name}")
        unet_file = os.path.join(file_path, file_name)
        self.pipe.unet.state_dict = torch.load(unet_file, map_location="cuda")

    def __apply_torch_compile(self):
        """
        Torch compile has limited support
            - No support for Windows
            - Fails with the compiled version of AI Runner
        Because of this, we are disabling it until a better solution is found.
        """
        if not self.settings["memory_settings"]["use_torch_compile"] or self.torch_compile_applied:
            return
        # unet_path = self.unet_model_path
        # if unet_path is None or unet_path == "":
        #     unet_path = os.path.join(self.model_base_path, "compiled_unet")
        # file_path = os.path.join(os.path.join(unet_path, self.model_path))
        model_name = self.settings["generator_settings"]["model"]
        # file_name = f"{model_name}.pt"
        # if os.path.exists(os.path.join(file_path, file_name)):
        #     self.load_unet(file_path, file_name)
        #     self.pipe.unet.to(memory_format=torch.channels_last)
        # else:
        self.logger.debug(f"Compiling torch model {model_name}")
        #self.pipe.unet.to(memory_format=torch.channels_last)
        self.pipe.unet = torch.compile(self.pipe.unet, mode="reduce-overhead", fullgraph=True)
        self.pipe(prompt=self.sd_request.generator_settings.prompt)
        # self.save_unet(file_path, file_name)
        self.torch_compile_applied = True
    
    def __apply_torch_trace(self):
        self.pipe.unet = TracedUNet(self.pipe)

    def __save_torch_trace(self):
        torch.set_grad_enabled(False)
        unet = self.pipe.unet
        unet.eval()
        unet.to(memory_format=torch.channels_last)  # use channels_last memory format
        unet.forward = functools.partial(unet.forward, return_dict=False)

        def generate_inputs():
            sample = torch.randn(2, 4, 64, 64).half().cuda()
            timestep = torch.rand(1).half().cuda() * 999
            encoder_hidden_states = torch.randn(2, 77, 768).half().cuda()
            return sample, timestep, encoder_hidden_states

        # warmup
        for _ in range(3):
            with torch.inference_mode():
                inputs = generate_inputs()
                orig_output = unet(*inputs)
        
        # trace
        print("tracing..")
        unet_traced = torch.jit.trace(unet, inputs)
        unet_traced.eval()
        print("done tracing")
        unet_traced.save("unet_traced.pt")

    def __enable_memory_chunking(self):
        return

    def __move_stable_diffusion_to_cuda(self):
        self.__move_pipe_to_cuda()

    def __move_pipe_to_cuda(self):
        if (
            self.use_enable_sequential_cpu_offload == self.settings["memory_settings"]["use_enable_sequential_cpu_offload"] and
            self.enable_model_cpu_offload == self.settings["memory_settings"]["enable_model_cpu_offload"]
        ):
            # Return if memory settings have not changed
            return

        self.use_enable_sequential_cpu_offload = self.settings["memory_settings"]["use_enable_sequential_cpu_offload"]
        self.enable_model_cpu_offload = self.settings["memory_settings"]["enable_model_cpu_offload"]

        # Keep track of applied memory settings
        if (
            self.cuda_is_available and not (
                self.use_enable_sequential_cpu_offload or
                self.enable_model_cpu_offload
            )
        ):
            if not str(self.pipe.device).startswith("cuda"):
                self.logger.debug(f"Moving pipe to cuda (currently {self.pipe.device})")
                clear_memory()
                try:
                    self.pipe.to("cuda", self.data_type)
                except Exception as e:
                    self.logger.error(f"Error moving to cuda: {e}")
            if hasattr(self.pipe, "controlnet") and self.pipe.controlnet is not None:
                try:
                    if str(self.pipe.controlnet.device).startswith("cuda"):
                        self.logger.debug(f"Moving controlnet to cuda (currently {self.pipe.controlnet.device})")
                        self.pipe.controlnet.half().to("cuda")
                except Exception as e:
                    self.logger.error(f"Error moving controlnet to cuda: {e}")

                try:
                    if not self.pipe.controlnet.dtype == torch.float16:
                        self.logger.debug("Changing controlnet dtype to float16")
                        self.pipe.controlnet.half()
                except Exception as e:
                    self.logger.error(f"Error changing controlnet dtype to float16: {e}")

    def __move_controlnet_to_cuda(self):
        try:
            self.controlnet.to("cuda", self.data_type)
        except Exception as e:
            self.logger.error(f"Error moving controlnet to cuda: {e}")
            self.logger.error(e)

    def __move_stable_diffusion_to_cpu(self):
        self.__move_pipe_to_cpu()
        self.__move_controlnet_to_cpu()

    def __move_pipe_to_cpu(self):
        self.logger.debug("Moving to cpu")
        try:
            self.pipe.to("cpu", self.data_type)
            self.emit_signal(
                SignalCode.PIPE_MOVED_SIGNAL, {
                    "model": ModelType.SD,
                    "device": DeviceName.CPU
                }
            )
        except Exception as e:
            self.logger.error(f"Error moving to cpu: {e}")

    def __move_controlnet_to_cpu(self):
        try:
            self.pipe.controlnet.to("cpu", self.data_type)
            self.emit_signal(
                SignalCode.PIPE_MOVED_SIGNAL, {
                    "model": ModelType.CONTROLNET,
                    "device": DeviceName.CPU
                }
            )
        except Exception as e:
            self.logger.warning("Not implemented error when moving to cpu")
            self.logger.warning(e)

    def __apply_cpu_offload(self):
        if self.cpu_offload_applied == self.settings["memory_settings"]["enable_model_cpu_offload"]:
            return
        self.cpu_offload_applied = self.settings["memory_settings"]["enable_model_cpu_offload"]

        if self.settings["memory_settings"]["use_enable_sequential_cpu_offload"] and not self.settings["memory_settings"]["enable_model_cpu_offload"]:
            self.logger.debug("Enabling sequential cpu offload")
            self.__move_stable_diffusion_to_cpu()
            try:
                self.pipe.enable_sequential_cpu_offload()
            except NotImplementedError:
                self.logger.warning("Not implemented error when applying sequential cpu offload")
                self.__move_stable_diffusion_to_cuda()

    def __apply_model_offload(self):
        if self.model_cpu_offload_applied == self.settings["memory_settings"]["enable_model_cpu_offload"]:
            return
        self.model_cpu_offload_applied = self.settings["memory_settings"]["enable_model_cpu_offload"]

        if self.settings["memory_settings"]["enable_model_cpu_offload"] \
           and not self.settings["memory_settings"]["use_enable_sequential_cpu_offload"] \
           and hasattr(self.pipe, "enable_model_cpu_offload"):
            self.logger.debug("Enabling model cpu offload")
            self.__move_stable_diffusion_to_cpu()
            self.pipe.enable_model_cpu_offload()
    
    def __apply_tome(self):
        """
        Conditionally apply and remove the ToMe SD weight merging.
        :return:
        """
        tome_sd_ratio = self.settings["memory_settings"]["tome_sd_ratio"] / 1000

        if self.use_tome_sd and (
            self.tome_sd_ratio != tome_sd_ratio or not
            self.tome_sd_applied
        ):
            self.tome_sd_ratio = tome_sd_ratio
            self.__remove_tome_sd()
            self.__apply_tome_sd(tome_sd_ratio)
        elif not self.use_tome_sd:
            self.__remove_tome_sd()

    def __remove_tome_sd(self):
        self.logger.debug("Removing ToMe SD weight merging")
        try:
            tomesd.remove_patch(self.pipe)
            self.tome_sd_applied = False
        except Exception as e:
            self.logger.error(f"Error removing ToMe SD weight merging: {e}")

    def __apply_tome_sd(self, tome_sd_ratio):
        self.logger.debug(f"Applying ToMe SD weight merging with ratio {tome_sd_ratio}")
        try:
            tomesd.apply_patch(self.pipe, ratio=tome_sd_ratio)
            self.tome_sd_applied = True
        except Exception as e:
            self.logger.error(f"Error applying ToMe SD weight merging: {e}")
            self.tome_sd_applied = False

