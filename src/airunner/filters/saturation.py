from PIL import ImageEnhance

from airunner.filters.base_filter import BaseFilter


class SaturationFilter(BaseFilter):
    """Adjust the color saturation of an image.
    
    This filter enhances or reduces the intensity of colors in the image.
    
    Attributes:
        factor: Saturation adjustment parameter (0-100, with 50 being neutral).
    """
    
    def apply_filter(self, image, do_reset=False):
        """Apply saturation adjustment to the image.
        
        Args:
            image: The PIL Image to filter.
            do_reset: Whether to reset internal state (unused in this filter).
            
        Returns:
            The saturation-adjusted PIL Image.
        """
        # Transform self.factor from [0, 100] to [-1, 2]
        factor = (self.factor - 50) / 25 + 1
        
        # Limit factor to 2 decimal places
        factor = round(factor, 2)
        
        return ImageEnhance.Color(image).enhance(factor)
