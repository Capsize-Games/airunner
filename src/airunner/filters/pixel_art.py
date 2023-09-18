from PIL import Image

from airunner.filters.base_filter import BaseFilter


class PixelFilter(BaseFilter):
    current_number_of_colors = 0

    def apply_filter(self, image, do_reset):
        # Reduce number of colors
        if self.current_number_of_colors != self.number_of_colors or do_reset:
            self.current_number_of_colors = self.number_of_colors
            quantized = image.quantize(self.number_of_colors)
            self.image = quantized.convert("RGBA")

        image = self.image
        # Downsize while maintaining aspect ratio
        width, height = image.size
        scale = min(self.base_size / width, self.base_size / height)
        new_width = int(width * scale)
        new_height = int(height * scale)
        downsized = image.resize((new_width, new_height), Image.NEAREST)

        # Upscale back to original dimensions
        target_width = int(new_width / scale)
        target_height = int(new_height / scale)
        final_image = downsized.resize((target_width, target_height), Image.NEAREST)

        return final_image
