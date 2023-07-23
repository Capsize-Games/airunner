from PIL import Image, ImageFilter, ImageChops


class RegistrationErrorFilter(ImageFilter.Filter):
    name = "Registration Error Filter"
    red_offset_x_amount = 1
    red_offset_y_amount = 1
    green_offset_x_amount = 1
    green_offset_y_amount = 1
    blue_offset_x_amount = 1
    blue_offset_y_amount = 1
    current_offset_amount = 1

    def __init__(
        self,
        red_offset_x_amount=1,
        red_offset_y_amount=1,
        green_offset_x_amount=1,
        green_offset_y_amount=1,
        blue_offset_x_amount=1,
        blue_offset_y_amount=1
    ):
        self.red_offset_x_amount = red_offset_x_amount
        self.red_offset_y_amount = red_offset_y_amount
        self.green_offset_x_amount = green_offset_x_amount
        self.green_offset_y_amount = green_offset_y_amount
        self.blue_offset_x_amount = blue_offset_x_amount
        self.blue_offset_y_amount = blue_offset_y_amount
        self.image = None
        self.image_id = None

    def filter(self, image):
        # first, split the image into its R G B channels
        r, g, b, a = image.split()

        # create a new image that is transparent and the same size
        r_image = Image.new("L", image.size)
        g_image = Image.new("L", image.size)
        b_image = Image.new("L", image.size)

        # now paste the r g b channels into the respective image, and offset each channel by the offset amount
        r_image.paste(r, (self.red_offset_x_amount, self.red_offset_y_amount))
        g_image.paste(g, (self.green_offset_x_amount, self.green_offset_y_amount))
        b_image.paste(b, (self.blue_offset_x_amount, self.blue_offset_y_amount))

        # merge the offset images
        offset_image = Image.merge("RGBA", [r_image, g_image, b_image, a])

        # return the offset image
        return offset_image
