from PIL import Image
from airunner.filters.base_filter import BaseFilter


class PixelFilter(BaseFilter):
    current_number_of_colors = 0

    def apply_filter(self, image, do_reset):
        # Reduce number of colors
        number_of_colors = getattr(self, "number_of_colors", 24)
        base_size = getattr(self, "base_size", 256)
        # ensure number_of_colors is an integer divisible by 2
        number_of_colors = int(number_of_colors) // 2 * 2
        if self.current_number_of_colors != number_of_colors or do_reset:
            try:
                self.current_number_of_colors = number_of_colors
                quantized = image.quantize(number_of_colors)
                self.image = quantized.convert("RGBA")
            except ValueError:
                print("Bad number of colors")

        image = self.image
        # Downsize while maintaining aspect ratio
        width, height = image.size
        scale = min(base_size / width, base_size / height)
        new_width = int(width * scale)
        new_height = int(height * scale)
        downsized = image.resize((new_width, new_height), Image.Resampling.NEAREST)

        # Upscale back to original dimensions
        target_width = int(new_width / scale)
        target_height = int(new_height / scale)
        final_image = downsized.resize((target_width, target_height), Image.Resampling.NEAREST)

        return final_image
