from PIL import ImageOps

from airunner.filters.base_filter import BaseFilter


class Invert(BaseFilter):
    """Invert the colors of an image.
    
    This filter creates a negative image by inverting the color values.
    """
    
    def apply_filter(self, image, do_reset=False):
        """Apply color inversion to the image.
        
        Args:
            image: The PIL Image to filter.
            do_reset: Whether to reset internal state (unused in this filter).
            
        Returns:
            The color-inverted PIL Image.
        """
        # Ensure the image is in RGB mode
        image = image.convert("RGB")
        # Invert the colors
        return ImageOps.invert(image)
