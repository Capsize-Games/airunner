import numpy as np
from PIL import Image

from airunner.filters.base_filter import BaseFilter


class RGBNoiseFilter(BaseFilter):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.red_grain = None
        self.green_grain = None
        self.blue_grain = None

    def apply_filter(self, image, do_reset):
        # Convert input values from 0-100 scale to 0-255 for pixel values
        red_intensity = float(getattr(self, "red", 0.0))
        green_intensity = float(getattr(self, "green", 0.0))
        blue_intensity = float(getattr(self, "blue", 0.0))
        
        # If all noise values are 0, just return the original image
        if red_intensity == 0.0 and green_intensity == 0.0 and blue_intensity == 0.0:
            return image
            
        # Ensure image is in RGBA mode
        image = image.convert("RGBA")
        
        # Get image dimensions
        width, height = image.size
        
        # Create a new image for the result
        result = Image.new('RGBA', (width, height))
        
        # Get access to pixel data
        img_data = image.load()
        result_data = result.load()
        
        # For each pixel, add random noise to RGB channels
        for y in range(height):
            for x in range(width):
                r, g, b, a = img_data[x, y]
                
                # Apply noise to each channel
                noisy_r = min(255, max(0, r + int(np.random.uniform(-red_intensity, red_intensity))))
                noisy_g = min(255, max(0, g + int(np.random.uniform(-green_intensity, green_intensity))))
                noisy_b = min(255, max(0, b + int(np.random.uniform(-blue_intensity, blue_intensity))))
                
                # Set the pixel in the result image
                result_data[x, y] = (noisy_r, noisy_g, noisy_b, a)
        
        return result
