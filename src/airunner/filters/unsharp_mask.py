from PIL.ImageFilter import UnsharpMask as PILUnsharpMask

from airunner.filters.base_filter import BaseFilter


class UnsharpMask(BaseFilter):
    """Apply an unsharp mask filter to an image.
    
    This filter enhances edges and details by applying an unsharp mask.
    
    Attributes:
        radius: Controls the size of the edges to enhance.
        percent: Controls the amount of enhancement.
        threshold: Controls the minimum brightness change to be enhanced.
    """
    
    def apply_filter(self, image, do_reset=False):
        """Apply unsharp mask filter to the image.
        
        Args:
            image: The PIL Image to filter.
            do_reset: Whether to reset internal state (unused in this filter).
            
        Returns:
            The sharpened PIL Image.
        """
        return image.filter(
            PILUnsharpMask(
                radius=self.radius * 100,
                percent=int(self.percent * 200),
                threshold=int(self.threshold * 10)
            )
        )
