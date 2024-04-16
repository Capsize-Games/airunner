from PIL import Image
from airunner.filters.base_filter import BaseFilter


class RegistrationErrorFilter(BaseFilter):
    def apply_filter(self, image, do_reset):
        image = image.convert("RGBA")
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
