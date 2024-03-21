import cv2
import numpy as np
import torch
from PIL import Image
from basicsr.utils import imwrite
from gfpgan import GFPGANer
from realesrgan import RealESRGANer
from basicsr.archs.rrdbnet_arch import RRDBNet


class RealESRGAN:
    def __init__(self, model_name: str, denoise_strength: float, face_enhance: bool):
        self.model_name = model_name
        self.denoise_strength = denoise_strength
        self.face_enhance = face_enhance
        self.bg_upsampler = self._setup_bg_upsampler()
        self.restorer = self._setup_gfpganer()

    def _setup_bg_upsampler(self):
        if not torch.cuda.is_available():  # Assuming CPU mode, simplify for demonstration
            return None
        model = RRDBNet(num_in_ch=3, num_out_ch=3, num_feat=64, num_block=23, num_grow_ch=32, scale=2)
        bg_upsampler = RealESRGANer(
            scale=2,
            model_path='https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.1/RealESRGAN_x2plus.pth',
            model=model,
            tile=400,
            tile_pad=10,
            pre_pad=0,
            half=True)  # need to set False in CPU mode
        return bg_upsampler

    def _setup_gfpganer(self):
        # Simplify for demonstration, choose model based on provided name
        model_path = f'https://github.com/TencentARC/GFPGAN/releases/download/v1.3.0/{self.model_name}.pth'
        restorer = GFPGANer(
            model_path=model_path,
            upscale=2,
            arch='clean',  # Simplification, should be determined by model_name
            channel_multiplier=2,
            bg_upsampler=self.bg_upsampler)
        return restorer

    def enhance(self, input_image: Image):
        # Convert PIL to cv2 image
        input_cv2 = cv2.cvtColor(np.array(input_image), cv2.COLOR_RGB2BGR)

        # Enhance image
        _, _, restored_img = self.restorer.enhance(
            input_cv2,
            has_aligned=False,
            only_center_face=False,
            paste_back=True,
            weight=self.denoise_strength)

        # Convert cv2 image back to PIL
        restored_pil = Image.fromarray(cv2.cvtColor(restored_img, cv2.COLOR_BGR2RGB))
        return restored_pil
