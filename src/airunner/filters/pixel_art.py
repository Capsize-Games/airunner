from PIL import Image, ImageFilter

from airunner.filters.base_filter import BaseFilter


class PixelFilter(BaseFilter):
    """Apply a pixel art effect to an image.
    
    This filter creates a pixel art effect by reducing colors and
    resizing the image with nearest-neighbor sampling.
    
    Attributes:
        number_of_colors: Number of colors to use in the quantized image.
        base_size: Base size for downscaling step.
        smoothing: Amount of smoothing to apply (0 for none).
    """
    
    def __init__(self, **kwargs):
        """Initialize the pixel art filter.
        
        Args:
            **kwargs: Arbitrary keyword arguments that will be set as
                     attributes on the filter instance.
        """
        super().__init__(**kwargs)
        self.current_number_of_colors = 0
    
    def apply_filter(self, image, do_reset=False):
        """Apply pixel art filter to the image.
        
        Args:
            image: The PIL Image to filter.
            do_reset: Whether to reset internal state.
            
        Returns:
            The pixel art PIL Image.
        """
        # Retrieve filter parameters with defaults
        number_of_colors = getattr(self, "number_of_colors", 24)
        base_size = getattr(self, "base_size", 256)
        smoothing = getattr(self, "smoothing", 0)
        
        # Ensure number_of_colors is an integer divisible by 2
        number_of_colors = int(number_of_colors) // 2 * 2
        
        # Quantize the image (reduce colors) if needed
        if self.current_number_of_colors != number_of_colors or do_reset:
            try:
                self.current_number_of_colors = number_of_colors
                quantized = image.quantize(number_of_colors)
                self.image = quantized.convert("RGBA")
            except ValueError:
                self.logger.debug("Bad number of colors")
        
        image = self.image
        
        # Downsize while maintaining aspect ratio
        width, height = image.size
        scale = min(base_size / width, base_size / height)
        new_width = int(width * scale)
        new_height = int(height * scale)
        downsized = image.resize(
            (new_width, new_height), 
            Image.Resampling.NEAREST
        )
        
        # Upscale back to original dimensions
        target_width = int(new_width / scale)
        target_height = int(new_height / scale)
        final_image = downsized.resize(
            (target_width, target_height), 
            Image.Resampling.NEAREST
        )
        
        # Apply smoothing if enabled
        if smoothing > 0:
            for _ in range(smoothing // 10):  # Apply smoothing filter multiple times
                final_image = final_image.filter(ImageFilter.SMOOTH)
        
        return final_image
