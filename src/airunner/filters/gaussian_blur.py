from PIL.ImageFilter import GaussianBlur as PILGaussianBlur

from airunner.filters.base_filter import BaseFilter


class GaussianBlur(BaseFilter):
    """Apply a Gaussian blur filter to an image.
    
    This filter performs a Gaussian blur with a specified radius.
    
    Attributes:
        radius: The radius of the Gaussian blur effect.
    """
    
    def apply_filter(self, image, do_reset=False):
        """Apply Gaussian blur filter to the image.
        
        Args:
            image: The PIL Image to filter.
            do_reset: Whether to reset internal state (unused in this filter).
            
        Returns:
            The Gaussian-blurred PIL Image.
        """
        return image.filter(PILGaussianBlur(radius=self.radius))
