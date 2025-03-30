from PIL import Image, ImageFilter
import numpy as np

from airunner.filters.base_filter import BaseFilter
from airunner.filters.box_blur import BoxBlur


class FilmFilter(BaseFilter):
    current_number_of_colors = 0
    
    def apply_filter(self, image, do_reset):
        # Get attribute values for both operations
        radius = float(getattr(self, "radius", 0.0))
        red_intensity = float(getattr(self, "red", 0.0))
        green_intensity = float(getattr(self, "green", 0.0))
        blue_intensity = float(getattr(self, "blue", 0.0))
        
        # Early return if no effect should be applied
        if radius == 0.0 and red_intensity == 0.0 and green_intensity == 0.0 and blue_intensity == 0.0:
            return image
        
        # Ensure image is in RGBA mode
        image = image.convert("RGBA")
        
        # Apply blur first if radius is non-zero
        if radius > 0:
            # Use built-in PIL blur since it's optimized
            image = image.filter(ImageFilter.BoxBlur(radius=radius))
        
        # Apply noise if any noise value is non-zero
        if red_intensity > 0 or green_intensity > 0 or blue_intensity > 0:
            # Convert to numpy array for fast processing
            image_array = np.array(image)
            height, width = image_array.shape[:2]
            
            # Generate noise arrays for each channel
            red_noise = np.random.uniform(-red_intensity, red_intensity, (height, width)).astype(np.int16)
            green_noise = np.random.uniform(-green_intensity, green_intensity, (height, width)).astype(np.int16)
            blue_noise = np.random.uniform(-blue_intensity, blue_intensity, (height, width)).astype(np.int16)
            
            # Apply noise to each channel
            r_channel = image_array[:, :, 0].astype(np.int16) + red_noise
            g_channel = image_array[:, :, 1].astype(np.int16) + green_noise
            b_channel = image_array[:, :, 2].astype(np.int16) + blue_noise
            
            # Clip values to valid range [0, 255]
            image_array[:, :, 0] = np.clip(r_channel, 0, 255).astype(np.uint8)
            image_array[:, :, 1] = np.clip(g_channel, 0, 255).astype(np.uint8)
            image_array[:, :, 2] = np.clip(b_channel, 0, 255).astype(np.uint8)
            
            # Convert back to PIL image
            image = Image.fromarray(image_array)
        
        return image
