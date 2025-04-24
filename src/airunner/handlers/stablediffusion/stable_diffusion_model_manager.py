import os

from diffusers.pipelines.stable_diffusion.pipeline_stable_diffusion import (
    StableDiffusionPipeline,
)
from diffusers.pipelines.stable_diffusion.pipeline_stable_diffusion_img2img import (
    StableDiffusionImg2ImgPipeline,
)
from diffusers.pipelines.stable_diffusion.pipeline_stable_diffusion_inpaint import (
    StableDiffusionInpaintPipeline,
)
from diffusers.pipelines.controlnet.pipeline_controlnet import (
    StableDiffusionControlNetPipeline,
)
from diffusers.pipelines.controlnet.pipeline_controlnet_img2img import (
    StableDiffusionControlNetImg2ImgPipeline,
)
from diffusers.pipelines.controlnet.pipeline_controlnet_inpaint import (
    StableDiffusionControlNetInpaintPipeline,
)
from diffusers.pipelines.stable_diffusion_xl.pipeline_stable_diffusion_xl import (
    StableDiffusionXLPipeline,
)
from diffusers.pipelines.stable_diffusion_xl.pipeline_stable_diffusion_xl_img2img import (
    StableDiffusionXLImg2ImgPipeline,
)
from diffusers.pipelines.stable_diffusion_xl.pipeline_stable_diffusion_xl_inpaint import (
    StableDiffusionXLInpaintPipeline,
)
from diffusers.pipelines.controlnet.pipeline_controlnet_sd_xl import (
    StableDiffusionXLControlNetPipeline,
)
from diffusers.pipelines.controlnet.pipeline_controlnet_sd_xl_img2img import (
    StableDiffusionXLControlNetImg2ImgPipeline,
)
from diffusers.pipelines.controlnet.pipeline_controlnet_inpaint_sd_xl import (
    StableDiffusionXLControlNetInpaintPipeline,
)
from airunner.enums import StableDiffusionVersion
from airunner.handlers import BaseDiffusersModelManager


class StableDiffusionModelManager(BaseDiffusersModelManager):
    @property
    def img2img_pipelines(self):
        return (
            StableDiffusionXLImg2ImgPipeline,
            StableDiffusionXLControlNetImg2ImgPipeline,
            StableDiffusionImg2ImgPipeline,
            StableDiffusionControlNetImg2ImgPipeline,
        )

    @property
    def txt2img_pipelines(self):
        return (
            StableDiffusionXLPipeline,
            StableDiffusionXLControlNetPipeline,
            StableDiffusionPipeline,
            StableDiffusionControlNetPipeline,
        )

    @property
    def controlnet_pipelines(self):
        return (
            StableDiffusionControlNetPipeline,
            StableDiffusionControlNetImg2ImgPipeline,
            StableDiffusionControlNetInpaintPipeline,
            StableDiffusionXLControlNetPipeline,
            StableDiffusionXLControlNetImg2ImgPipeline,
            StableDiffusionXLControlNetInpaintPipeline,
        )

    @property
    def outpaint_pipelines(self):
        return (
            StableDiffusionXLInpaintPipeline,
            StableDiffusionInpaintPipeline,
            StableDiffusionControlNetInpaintPipeline,
            StableDiffusionXLControlNetInpaintPipeline,
        )

    @property
    def is_sd_xl(self) -> bool:
        return self.real_model_version == StableDiffusionVersion.SDXL1_0.value

    @property
    def is_sd_xl_turbo(self) -> bool:
        return (
            self.real_model_version == StableDiffusionVersion.SDXL_TURBO.value
        )

    @property
    def is_sd_xl_or_turbo(self) -> bool:
        return self.is_sd_xl or self.is_sd_xl_turbo

    @property
    def config_path(self) -> str:
        if self.is_sd_xl_turbo:
            return os.path.expanduser(
                os.path.join(
                    self.path_settings_cached.base_path,
                    "art",
                    "models",
                    StableDiffusionVersion.SDXL1_0.value,
                    self.image_request.pipeline_action,
                )
            )
        return super().config_path

    @property
    def _pipeline_class(self):
        operation_type = "txt2img"
        if self.is_img2img:
            operation_type = "img2img"
        elif self.is_outpaint:
            operation_type = "outpaint"

        if self.controlnet_enabled:
            operation_type = f"{operation_type}_controlnet"

        if self.is_sd_xl_or_turbo:
            pipeline_map = {
                "txt2img": StableDiffusionXLPipeline,
                "img2img": StableDiffusionXLImg2ImgPipeline,
                "outpaint": StableDiffusionXLInpaintPipeline,
                "txt2img_controlnet": StableDiffusionXLControlNetPipeline,
                "img2img_controlnet": StableDiffusionXLControlNetImg2ImgPipeline,
                "outpaint_controlnet": StableDiffusionXLControlNetInpaintPipeline,
            }
        else:
            pipeline_map = {
                "txt2img": StableDiffusionPipeline,
                "img2img": StableDiffusionImg2ImgPipeline,
                "outpaint": StableDiffusionInpaintPipeline,
                "txt2img_controlnet": StableDiffusionControlNetPipeline,
                "img2img_controlnet": StableDiffusionControlNetImg2ImgPipeline,
                "outpaint_controlnet": StableDiffusionControlNetInpaintPipeline,
            }
        return pipeline_map.get(operation_type)
