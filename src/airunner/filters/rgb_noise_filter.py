from PIL import Image, ImageFilter


class RGBNoiseFilter(ImageFilter.Filter):
    name = "RGB Noise Filter"
    red_grain = None
    green_grain = None
    blue_grain = None

    def __init__(self, red, green, blue, red_grain, green_grain, blue_grain):
        self.red = red
        self.green = green
        self.blue = blue
        self.red_grain = red_grain
        self.green_grain = green_grain
        self.blue_grain = blue_grain

    def filter(self, image):
        red, green, blue, alpha = image.split()
        red = Image.blend(red, self.red_grain, self.red)
        green = Image.blend(green, self.green_grain, self.green)
        blue = Image.blend(blue, self.blue_grain, self.blue)
        image = Image.merge("RGBA", (red, green, blue, alpha))
        return image