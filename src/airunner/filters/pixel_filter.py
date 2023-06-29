from PIL import Image, ImageFilter


class PixelFilter(ImageFilter.Filter):
    name = "Resize Filter"
    current_number_of_colors = 0

    def __init__(self, number_of_colors=24, smoothing=1, base_size=16):
        self.number_of_colors = number_of_colors
        self.smoothing = smoothing
        self.base_size = base_size
        self.image = None
        self.image_id = None

    def filter(self, image):
        reset_colors = False
        if not self.image_id or self.image_id != id(image):
            self.image_id = id(image)
            self.image = image
            reset_colors = True

        # Reduce number of colors
        if self.current_number_of_colors != self.number_of_colors or reset_colors:
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
