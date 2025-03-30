from PIL import Image

from airunner.filters.base_filter import BaseFilter


class RegistrationErrorFilter(BaseFilter):
    """Apply a registration error effect to an image.
    
    This filter simulates color channel misalignment by offsetting
    the red, green, and blue channels independently.
    
    Attributes:
        red_offset_x_amount: Horizontal offset for the red channel.
        red_offset_y_amount: Vertical offset for the red channel.
        green_offset_x_amount: Horizontal offset for the green channel.
        green_offset_y_amount: Vertical offset for the green channel.
        blue_offset_x_amount: Horizontal offset for the blue channel.
        blue_offset_y_amount: Vertical offset for the blue channel.
    """
    
    def apply_filter(self, image, do_reset=False):
        """Apply registration error filter to the image.
        
        Args:
            image: The PIL Image to filter.
            do_reset: Whether to reset internal state (unused in this filter).
            
        Returns:
            The filtered PIL Image with channel offsets.
        """
        image = image.convert("RGBA")
        
        # Split the image into its R, G, B, A channels
        r, g, b, a = image.split()
        
        # Create new single-channel images for each component
        r_image = Image.new("L", image.size)
        g_image = Image.new("L", image.size)
        b_image = Image.new("L", image.size)
        
        # Paste the channels with their respective offsets
        r_image.paste(r, (self.red_offset_x_amount, self.red_offset_y_amount))
        g_image.paste(g, (self.green_offset_x_amount, self.green_offset_y_amount))
        b_image.paste(b, (self.blue_offset_x_amount, self.blue_offset_y_amount))
        
        # Merge the offset channels with the original alpha
        return Image.merge("RGBA", [r_image, g_image, b_image, a])
