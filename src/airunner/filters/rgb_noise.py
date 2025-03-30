import numpy as np
from PIL import Image

from airunner.filters.base_filter import BaseFilter


class RGBNoiseFilter(BaseFilter):
    """Apply RGB noise to an image.
    
    This filter adds random noise to each color channel independently.
    
    Attributes:
        red: Intensity of noise to add to the red channel.
        green: Intensity of noise to add to the green channel.
        blue: Intensity of noise to add to the blue channel.
    """
    
    def __init__(self, **kwargs):
        """Initialize the RGB noise filter.
        
        Args:
            **kwargs: Arbitrary keyword arguments that will be set as
                     attributes on the filter instance.
        """
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
        
        # Convert image to numpy array (much faster for processing)
        image_array = np.array(image)
        
        # Generate random noise for all pixels at once
        height, width = image_array.shape[:2]
        
        # Generate noise arrays for each channel all at once
        red_noise = np.random.uniform(-red_intensity, red_intensity, (height, width)).astype(np.int16)
        green_noise = np.random.uniform(-green_intensity, green_intensity, (height, width)).astype(np.int16)
        blue_noise = np.random.uniform(-blue_intensity, blue_intensity, (height, width)).astype(np.int16)
        
        # Apply noise to all pixels simultaneously
        # Convert to int16 first to prevent overflow
        r_channel = image_array[:, :, 0].astype(np.int16) + red_noise
        g_channel = image_array[:, :, 1].astype(np.int16) + green_noise
        b_channel = image_array[:, :, 2].astype(np.int16) + blue_noise
        
        # Clip values to valid range [0, 255]
        image_array[:, :, 0] = np.clip(r_channel, 0, 255).astype(np.uint8)
        image_array[:, :, 1] = np.clip(g_channel, 0, 255).astype(np.uint8)
        image_array[:, :, 2] = np.clip(b_channel, 0, 255).astype(np.uint8)
        
        # Convert back to PIL image
        result = Image.fromarray(image_array)
        
        return result
