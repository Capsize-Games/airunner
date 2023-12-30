from PIL import Image
import numpy as np
import cv2
import glob
import os
from basicsr.archs.rrdbnet_arch import RRDBNet
from basicsr.utils.download_util import load_file_from_url
import sys
import os

# Get the directory containing the current file
current_dir = os.path.dirname(os.path.abspath(__file__))

# Get the parent directory
parent_dir = os.path.dirname(os.path.join(current_dir, "realesrgan"))

# Add the parent directory to Python's path
sys.path.append(parent_dir)

# Now you should be able to import the realesrgan module
from airunner.scripts.realesrgan.utils import RealESRGANer
from basicsr.archs.srvgg_arch import SRVGGNetCompact


class RealESRGAN:
    def __init__(
        self, 
        input='inputs', 
        model_name='RealESRGAN_x4plus', 
        output='results',
        denoise_strength=0.5, 
        outscale=4, 
        model_path=None, 
        suffix='out', 
        tile=0, 
        tile_pad=10, 
        pre_pad=0, 
        face_enhance=False, 
        fp32=False, 
        alpha_upsampler='realesrgan', 
        ext='auto', 
        gpu_id=None
    ):
        self.input = input
        self.model_name = model_name
        self.output = output
        self.denoise_strength = denoise_strength
        self.outscale = outscale
        self.model_path = model_path
        self.suffix = suffix
        self.tile = tile
        self.tile_pad = tile_pad
        self.pre_pad = pre_pad
        self.face_enhance = face_enhance
        self.fp32 = fp32
        self.alpha_upsampler = alpha_upsampler
        self.ext = ext
        self.gpu_id = gpu_id

    def run(self):
        # determine models according to model names
        self.model_name = self.model_name.split('.')[0]
        if self.model_name == 'RealESRGAN_x4plus':  # x4 RRDBNet model
            model = RRDBNet(num_in_ch=3, num_out_ch=3, num_feat=64, num_block=23, num_grow_ch=32, scale=4)
            netscale = 4
            file_url = ['https://github.com/xinntao/Real-ESRGAN/releases/download/v0.1.0/RealESRGAN_x4plus.pth']
        elif self.model_name == 'RealESRNet_x4plus':  # x4 RRDBNet model
            model = RRDBNet(num_in_ch=3, num_out_ch=3, num_feat=64, num_block=23, num_grow_ch=32, scale=4)
            netscale = 4
            file_url = ['https://github.com/xinntao/Real-ESRGAN/releases/download/v0.1.1/RealESRNet_x4plus.pth']
        elif self.model_name == 'RealESRGAN_x4plus_anime_6B':  # x4 RRDBNet model with 6 blocks
            model = RRDBNet(num_in_ch=3, num_out_ch=3, num_feat=64, num_block=6, num_grow_ch=32, scale=4)
            netscale = 4
            file_url = ['https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.2.4/RealESRGAN_x4plus_anime_6B.pth']
        elif self.model_name == 'RealESRGAN_x2plus':  # x2 RRDBNet model
            model = RRDBNet(num_in_ch=3, num_out_ch=3, num_feat=64, num_block=23, num_grow_ch=32, scale=2)
            netscale = 2
            file_url = ['https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.1/RealESRGAN_x2plus.pth']
        elif self.model_name == 'realesr-animevideov3':  # x4 VGG-style model (XS size)
            model = SRVGGNetCompact(num_in_ch=3, num_out_ch=3, num_feat=64, num_conv=16, upscale=4, act_type='prelu')
            netscale = 4
            file_url = ['https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.5.0/realesr-animevideov3.pth']
        elif self.model_name == 'realesr-general-x4v3':  # x4 VGG-style model (S size)
            model = SRVGGNetCompact(num_in_ch=3, num_out_ch=3, num_feat=64, num_conv=32, upscale=4, act_type='prelu')
            netscale = 4
            file_url = [
                'https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.5.0/realesr-general-wdn-x4v3.pth',
                'https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.5.0/realesr-general-x4v3.pth'
            ]

        # determine model paths
        if self.model_path is not None:
            model_path = self.model_path
        else:
            model_path = os.path.join('weights', self.model_name + '.pth')
            if not os.path.isfile(model_path):
                ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
                for url in file_url:
                    # model_path will be updated
                    model_path = load_file_from_url(
                        url=url, model_dir=os.path.join(ROOT_DIR, 'weights'), progress=True, file_name=None)

        # use dni to control the denoise strength
        dni_weight = None
        if self.model_name == 'realesr-general-x4v3' and self.denoise_strength != 1:
            wdn_model_path = model_path.replace('realesr-general-x4v3', 'realesr-general-wdn-x4v3')
            model_path = [model_path, wdn_model_path]
            dni_weight = [self.denoise_strength, 1 - self.denoise_strength]

        # restorer
        upsampler = RealESRGANer(
            scale=netscale,
            model_path=model_path,
            dni_weight=dni_weight,
            model=model,
            tile=self.tile,
            tile_pad=self.tile_pad,
            pre_pad=self.pre_pad,
            half=not self.fp32,
            gpu_id=self.gpu_id)

        if self.face_enhance:  # Use GFPGAN for face enhancement
            from gfpgan import GFPGANer
            face_enhancer = GFPGANer(
                model_path='https://github.com/TencentARC/GFPGAN/releases/download/v1.3.0/GFPGANv1.3.pth',
                upscale=self.outscale,
                arch='clean',
                channel_multiplier=2,
                bg_upsampler=upsampler)
        
        if self.output:
            os.makedirs(self.output, exist_ok=True)

        if isinstance(self.input, Image.Image):
            paths = [self.input]
        elif isinstance(self.input, list) and all(isinstance(i, Image.Image) for i in self.input):
            paths = self.input
        elif os.path.isfile(self.input):
            paths = [Image.open(self.input)]
        else:
            paths = [Image.open(i) for i in sorted(glob.glob(os.path.join(self.input, '*')))]

        output_images = []
        for idx, path in enumerate(paths):
            if isinstance(path, Image.Image):
                imgname = f'image_{idx}'
                img = np.array(path)
            else:
                img = cv2.imread(path.filename, cv2.IMREAD_UNCHANGED)

            if len(img.shape) == 3 and img.shape[2] == 4:
                img_mode = 'RGBA'
            else:
                img_mode = None

            try:
                if self.face_enhance:
                    _, _, output = face_enhancer.enhance(img, has_aligned=False, only_center_face=False, paste_back=True)
                else:
                    output, _ = upsampler.enhance(img, outscale=self.outscale)
            except RuntimeError as error:
                print('Error', error)
                print('If you encounter CUDA out of memory, try to set --tile with a smaller number.')
            else:
                output_image = Image.fromarray(output)
                output_images.append(output_image)

                if self.output is not None:
                    if self.ext == 'auto':
                        extension = 'png'
                    else:
                        extension = self.ext
                    if img_mode == 'RGBA':  # RGBA images should be saved in png format
                        extension = 'png'
                    if self.suffix == '':
                        save_path = os.path.join(self.output, f'{imgname}.{extension}')
                    else:
                        save_path = os.path.join(self.output, f'{imgname}_{self.suffix}.{extension}')
                    output_image.save(save_path)
        
        if self.output is None:
            return output_images if len(output_images) > 1 else output_images[0]