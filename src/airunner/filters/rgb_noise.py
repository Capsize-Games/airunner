import numpy as np
from PIL import Image, ImageChops

from airunner.filters.base_filter import BaseFilter


class RGBNoiseFilter(BaseFilter):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.red_grain = None
        self.green_grain = None
        self.blue_grain = None

    def apply_filter(self, image, do_reset):
        # Convert image to numpy array
        image_array = np.array(image)

        # Generate random noise
        red_noise = np.random.rand(*image.size) * self.red
        green_noise = np.random.rand(*image.size) * self.green
        blue_noise = np.random.rand(*image.size) * self.blue

        # Add noise to each channel
        image_array[..., 0] = np.clip(image_array[..., 0] + red_noise, 0, 255)
        image_array[..., 1] = np.clip(image_array[..., 1] + green_noise, 0, 255)
        image_array[..., 2] = np.clip(image_array[..., 2] + blue_noise, 0, 255)

        # Convert back to PIL image
        image = Image.fromarray(image_array.astype('uint8'), 'RGBA')
        return image
