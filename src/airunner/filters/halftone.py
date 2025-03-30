from PIL import Image, ImageDraw

from airunner.filters.base_filter import BaseFilter


class HalftoneFilter(BaseFilter):
    """Apply a halftone effect to an image.
    
    This filter creates a halftone effect by converting the image to a pattern
    of dots of varying sizes.
    
    Attributes:
        color_mode: The color mode to use ('L' for grayscale or 'RGB' for color).
        sample: The sampling rate for the halftone effect.
        scale: The scaling factor for the dots.
    """
    
    def apply_filter(self, image, do_reset=False):
        """Apply halftone filter to the image.
        
        Args:
            image: The PIL Image to filter.
            do_reset: Whether to reset internal state (unused in this filter).
            
        Returns:
            The halftone-filtered PIL Image.
        """
        img = image.convert(self.color_mode)
        sample = self.sample + 2
        width, height = img.size
        
        # Resize to smaller image for sampling
        img_small = img.resize((width // sample, height // sample))
        sm_width, sm_height = img_small.size
        
        # Create new image for the halftone effect
        img_large = Image.new(self.color_mode, (width, height))
        draw = ImageDraw.Draw(img_large)
        
        # Draw dots for each pixel in the sampled image
        for x in range(0, sm_width):
            for y in range(0, sm_height):
                color = img_small.getpixel((x, y))
                
                if self.color_mode == "L":
                    radius = (color / 255) * (sample // 2) * self.scale
                else:
                    radius = (color[0] / 255) * (sample // 2) * self.scale
                
                draw.ellipse([
                    (x * sample - radius, y * sample - radius),
                    (x * sample + radius, y * sample + radius)
                ], fill=color)
        
        # Convert to RGBA for consistent output
        return img_large.convert('RGBA')
