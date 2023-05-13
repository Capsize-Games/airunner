from PIL import Image, ImageFilter


class PixelFilter(ImageFilter.Filter):
    name = "Resize Filter"

    def __init__(self, number_of_colors=24, smoothing=1, base_size=16):
        self.number_of_colors = number_of_colors
        self.smoothing = smoothing
        self.base_size = base_size

    def filter(self, image):
        # Downsize while maintaining aspect ratio
        width, height = image.size
        scale = min(self.base_size / width, self.base_size / height)
        new_width = int(width * scale)
        new_height = int(height * scale)
        downsized = image.resize((new_width, new_height), Image.NEAREST)

        # Upscale back to original dimensions
        target_width = int(new_width / scale)
        target_height = int(new_height / scale)
        upscaled = downsized.resize((target_width, target_height), Image.NEAREST)

        # Reduce number of colors
        quantized = upscaled.quantize(self.number_of_colors)
        quantized = quantized.convert("L")
        return quantized
