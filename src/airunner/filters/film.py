from airunner.filters.base_filter import BaseFilter
from airunner.filters.box_blur import BoxBlur
from airunner.filters.rgb_noise import RGBNoiseFilter


class FilmFilter(BaseFilter):
    """Apply a film-like effect to an image.
    
    This filter combines a box blur and RGB noise to create a film-like effect.
    
    Attributes:
        radius: The radius for the box blur component.
        red: The intensity of red noise.
        green: The intensity of green noise.
        blue: The intensity of blue noise.
    """
    
    def apply_filter(self, image, do_reset=False):
        """Apply film filter to the image.
        
        Args:
            image: The PIL Image to filter.
            do_reset: Whether to reset internal state (unused in this filter).
            
        Returns:
            The filtered PIL Image with film effect.
        """
        image = BoxBlur(
            radius=self.radius
        ).filter(image)
        
        image = RGBNoiseFilter(
            red=self.red,
            green=self.green,
            blue=self.blue
        ).filter(image)
        
        return image
