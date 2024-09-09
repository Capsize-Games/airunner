import numpy as np
from PIL import Image

from airunner.filters.base_filter import BaseFilter

class Dither(BaseFilter):
    def apply_filter(self, image, do_reset):
        # Convert image to grayscale
        grayscale_image = image.convert('L')

        # Convert grayscale image to numpy array
        image_array = np.array(grayscale_image, dtype=float)

        # Calculate the threshold value
        max_value = 255
        threshold_value = self.threshold * max_value

        # Apply Floyd-Steinberg dithering
        for y in range(image_array.shape[0]):
            for x in range(image_array.shape[1]):
                old_pixel = image_array[y, x]
                new_pixel = 255 if old_pixel > threshold_value else 0
                image_array[y, x] = new_pixel
                quant_error = old_pixel - new_pixel

                if x + 1 < image_array.shape[1]:
                    image_array[y, x + 1] += quant_error * 7 / 16
                if y + 1 < image_array.shape[0]:
                    if x > 0:
                        image_array[y + 1, x - 1] += quant_error * 3 / 16
                    image_array[y + 1, x] += quant_error * 5 / 16
                    if x + 1 < image_array.shape[1]:
                        image_array[y + 1, x + 1] += quant_error * 1 / 16

        # Convert back to PIL image
        dithered_image = Image.fromarray(image_array.astype('uint8'), 'L')

        # Convert to black and white
        bw_image = dithered_image.convert('1')

        return bw_image
