from PIL.ImageFilter import BoxBlur as ImageFilterBoxBlur

from airunner.filters.base_filter import BaseFilter


class BoxBlur(BaseFilter):
    """Apply a box blur filter to an image.
    
    This filter performs a box blur with a specified radius.
    
    Attributes:
        radius: The radius of the box blur effect.
    """
    
    def apply_filter(self, image, do_reset=False):
        """Apply box blur filter to the image.
        
        Args:
            image: The PIL Image to filter.
            do_reset: Whether to reset internal state (unused in this filter).
            
        Returns:
            The box-blurred PIL Image.
        """
        return image.filter(ImageFilterBoxBlur(radius=self.radius))
