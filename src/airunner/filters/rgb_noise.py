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
    
    def apply_filter(self, image, do_reset=False):
        """Apply RGB noise filter to the image.
        
        Args:
            image: The PIL Image to filter.
            do_reset: Whether to reset internal state (unused in this filter).
            
        Returns:
            The noise-filtered PIL Image.
        """
        # Convert image to numpy array
        image_array = np.array(image)
        
        # Generate random noise for each channel
        red_noise = np.random.rand(*image.size) * self.red
        green_noise = np.random.rand(*image.size) * self.green
        blue_noise = np.random.rand(*image.size) * self.blue
        
        # Add noise to each channel, clipping to valid range [0, 255]
        image_array[..., 0] = np.clip(image_array[..., 0] + red_noise, 0, 255)
        image_array[..., 1] = np.clip(image_array[..., 1] + green_noise, 0, 255)
        image_array[..., 2] = np.clip(image_array[..., 2] + blue_noise, 0, 255)
        
        # Convert back to PIL image
        return Image.fromarray(image_array.astype('uint8'), 'RGBA')
