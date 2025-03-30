from PIL import Image

from airunner.filters.base_filter import BaseFilter


class ColorBalanceFilter(BaseFilter):
    """Adjust the color balance of an image.
    
    This filter allows adjusting the red, green, and blue channels
    independently to achieve color balance corrections.
    
    Attributes:
        cyan_red: Adjustment factor for the red channel.
        magenta_green: Adjustment factor for the green channel.
        yellow_blue: Adjustment factor for the blue channel.
    """
    
    def apply_filter(self, image, do_reset=False):
        """Apply color balance adjustments to the image.
        
        Args:
            image: The PIL Image to filter.
            do_reset: Whether to reset internal state (unused in this filter).
            
        Returns:
            The color-balanced PIL Image.
        """
        image = image.convert("RGBA")
        red, green, blue, alpha = image.split()
        
        red = red.point(lambda i: i + (i * self.cyan_red))
        green = green.point(lambda i: i + (i * self.magenta_green))
        blue = blue.point(lambda i: i + (i * self.yellow_blue))
        
        return Image.merge("RGBA", (red, green, blue, alpha))
