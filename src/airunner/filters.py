import os

from PIL import ImageEnhance, Image, ImageFilter
from PIL.ImageFilter import GaussianBlur, BoxBlur, UnsharpMask, Filter
from PyQt6 import uic
from aihandler.qtvar import FloatVar, IntVar


class ColorBalanceFilter(Filter):
    name = "Color Balance"

    def __init__(self, cyan_red=0, magenta_green=0, yellow_blue=0):
        self.cyan_red = cyan_red
        self.magenta_green = magenta_green
        self.yellow_blue = yellow_blue

    def filter(self, image):
        # Apply enhancement
        image = ImageEnhance.Color(image).enhance(1.0 + self.cyan_red)
        image = ImageEnhance.Color(image).enhance(1.0 + self.magenta_green)
        image = ImageEnhance.Color(image).enhance(1.0 + self.yellow_blue)
        return image


class SaturationFilter(Filter):
    name = "Saturation"

    def __init__(self, factor=1.0):
        self.factor = factor

    def filter(self, image):
        return ImageEnhance.Color(image).enhance(1.0 + self.factor)


class FilterBase:
    ui_name = ""
    window_title = ""

    @property
    def filter(self):
        return None

    def update_canvas(self):
        self.canvas.update()

    def __init__(self, parent):
        self.filter_window = None
        self.parent = parent
        self.canvas = parent.canvas

    def show(self):
        self.filter_window = uic.loadUi(os.path.join(f"pyqt/{self.ui_name}.ui"))
        self.filter_window.setWindowTitle(self.window_title)

    def cancel_filter(self):
        self.filter_window.close()
        self.parent.current_filter = None
        self.update_canvas()

    def apply_filter(self):
        self.canvas.apply_filter()
        self.filter_window.close()
        self.update_canvas()


class BlurFilter(FilterBase):
    ui_name = ""
    window_title = ""

    def __init__(self, parent):
        super().__init__(parent)
        self.blur_radius = parent.settings_manager.settings.blur_radius
        self.default_value = 0.0


    def show(self):
        super().show()
        self.blur_radius.set(self.default_value)

        self.parent.current_filter = self.filter

        blur_radius = self.blur_radius.get()

        # set the gaussian_blur_window settings values to the current settings
        self.filter_window.blur_slider.setValue(int(blur_radius))
        self.filter_window.blur_slider.valueChanged.connect(
            lambda val: self.handle_blur_radius_slider_change(val))
        self.filter_window.blur_spinbox.setValue(blur_radius)
        self.filter_window.blur_spinbox.valueChanged.connect(
            lambda val: self.handle_blur_radius_spinbox_change(val))

        # on ok button click, apply the filter
        self.filter_window.buttonBox.rejected.connect(self.cancel_filter)
        self.filter_window.buttonBox.accepted.connect(self.apply_filter)

        self.filter_window.exec()

    def handle_blur_radius_slider_change(self, val):
        self.blur_radius.set(float(val))
        self.filter_window.blur_spinbox.setValue(float(val))
        self.parent.current_filter = self.filter
        self.canvas.update()

    def handle_blur_radius_spinbox_change(self, val):
        self.blur_radius.set(val)
        self.filter_window.blur_slider.setValue(int(val))
        self.parent.current_filter = self.filter
        self.update_canvas()


class FilterGaussianBlur(BlurFilter):
    ui_name = "gaussian_blur_window"
    window_title = "Gaussian Blur"
    default_value = 0.5

    @property
    def filter(self):
        return GaussianBlur(radius=self.blur_radius.get())


class FilterBoxBlur(BlurFilter):
    ui_name = "box_blur_window"
    window_title = "Box Blur"
    default_value = 0.5

    @property
    def filter(self):
        return BoxBlur(radius=self.blur_radius.get())


class FilterPixelArt(FilterBase):
    ui_name = "pixel_art"
    window_title = "Pixel Art"
    number_of_colors = 24
    smoothing = 1
    base_size = 256

    @property
    def filter(self):
        return PixelFilter(
            number_of_colors=self.number_of_colors,
            smoothing=self.smoothing,
            base_size=self.base_size
        )

    def show(self):
        super().show()
        self.parent.current_filter = self.filter

        # set the gaussian_blur_window settings values to the current settings
        self.filter_window.number_of_colors_slider.setValue(self.number_of_colors)
        self.filter_window.number_of_colors_spinbox.setValue(self.number_of_colors)
        self.filter_window.number_of_colors_slider.valueChanged.connect(
            lambda val: self.handle_number_of_colors_change_slider(val))
        self.filter_window.number_of_colors_spinbox.valueChanged.connect(
            lambda val: self.handle_number_of_colors_change_spinbox(val))

        # ensure base_size is multiple of 16
        self.filter_window.base_size_slider.setValue(self.base_size)
        self.filter_window.base_size_spinbox.setValue(self.base_size)
        self.filter_window.base_size_slider.valueChanged.connect(
            lambda val: self.handle_base_size_change_slider(val))
        self.filter_window.base_size_spinbox.valueChanged.connect(
            lambda val: self.handle_base_size_change_spinbox(val))

        # on ok button click, apply the filter
        self.filter_window.buttonBox.rejected.connect(self.cancel_filter)
        self.filter_window.buttonBox.accepted.connect(self.apply_filter)

        # apply the filter
        self.parent.current_filter = self.filter
        self.canvas.apply_filter()
        self.update_canvas()

        self.filter_window.exec()

    def handle_number_of_colors_change_slider(self, val):
        self.handle_number_of_colors_change(val)
        self.filter_window.number_of_colors_spinbox.setValue(val)

    def handle_number_of_colors_change_spinbox(self, val):
        self.handle_number_of_colors_change(val)
        self.filter_window.number_of_colors_slider.setValue(val)

    def handle_number_of_colors_change(self, val):
        self.number_of_colors = val
        self.parent.current_filter = self.filter
        self.canvas.update()

    def handle_base_size_change_slider(self, val):
        val = val - (val % 16)
        self.handle_base_size_change(val)
        self.filter_window.base_size_spinbox.setValue(val)

    def handle_base_size_change_spinbox(self, val):
        val = val - (val % 16)
        self.handle_base_size_change(val)
        self.filter_window.base_size_slider.setValue(val)

    def handle_base_size_change(self, val):
        self.base_size = val
        self.parent.current_filter = self.filter
        self.canvas.update()


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


class FilterUnsharpMask(FilterBase):
    ui_name = "unsharp_mask_window"
    window_title = "Unsharp Mask"
    unsharp_radius = 0.5
    unsharp_percent = 0.5
    unsharp_threshold = 0.5

    @property
    def filter(self):
        return UnsharpMask(
            radius=self.unsharp_radius,
            percent=int(self.unsharp_percent),
            threshold=int(self.unsharp_threshold)
        )

    def show(self):
        super().show()

        self.unsharp_radius = 0.5
        self.unsharp_percent = 0.5
        self.unsharp_threshold = 0.5

        def update_filter():
            self.parent.current_filter = self.filter
            self.canvas.update()

        def handle_unsharp_radius_slider_change(val):
            self.unsharp_radius = val
            self.filter_window.radius_spinbox.setValue(val)
            self.filter_window.radius_spinbox.update()
            self.filter_window.radius_slider.update()
            update_filter()

        def handle_unsharp_radius_spinbox_change(val):
            self.unsharp_radius = val
            self.filter_window.radius_slider.setValue(int(val))
            self.filter_window.radius_spinbox.update()
            self.filter_window.radius_slider.update()
            update_filter()

        def handle_unsharp_percent_slider_change(val):
            self.unsharp_percent = val
            self.filter_window.percent_spinbox.setValue(val)
            self.filter_window.percent_spinbox.update()
            self.filter_window.percent_slider.update()
            update_filter()

        def handle_unsharp_percent_spinbox_change(val):
            self.unsharp_percent = val
            self.filter_window.percent_slider.setValue(int(val))
            self.filter_window.percent_spinbox.update()
            self.filter_window.percent_slider.update()
            update_filter()

        def handle_unsharp_threshold_slider_change(val):
            self.unsharp_threshold = val
            self.filter_window.threshold_spinbox.setValue(val)
            self.filter_window.threshold_spinbox.update()
            self.filter_window.threshold_slider.update()
            update_filter()

        def handle_unsharp_threshold_spinbox_change(val):
            self.unsharp_threshold = val
            self.filter_window.threshold_slider.setValue(int(val))
            self.filter_window.threshold_spinbox.update()
            self.filter_window.threshold_slider.update()
            update_filter()

        # set the gaussian_blur_window settings values to the current settings
        self.filter_window.radius_slider.setValue(int(self.unsharp_radius))
        self.filter_window.radius_slider.valueChanged.connect(lambda val: handle_unsharp_radius_slider_change(val))
        self.filter_window.radius_spinbox.setValue(self.unsharp_radius)
        self.filter_window.radius_spinbox.valueChanged.connect(lambda val: handle_unsharp_radius_spinbox_change(val))

        self.filter_window.percent_slider.setValue(int(self.unsharp_percent))
        self.filter_window.percent_slider.valueChanged.connect(lambda val: handle_unsharp_percent_slider_change(val))
        self.filter_window.percent_spinbox.setValue(self.unsharp_percent)
        self.filter_window.percent_spinbox.valueChanged.connect(lambda val: handle_unsharp_percent_spinbox_change(val))

        self.filter_window.threshold_slider.setValue(int(self.unsharp_threshold))
        self.filter_window.threshold_slider.valueChanged.connect(lambda val: handle_unsharp_threshold_slider_change(val))
        self.filter_window.threshold_spinbox.setValue(self.unsharp_threshold)
        self.filter_window.threshold_spinbox.valueChanged.connect(lambda val: handle_unsharp_threshold_spinbox_change(val))
        self.filter_window = self.filter_window
        # on ok button click, apply the filter
        self.filter_window.buttonBox.rejected.connect(self.cancel_filter)
        self.filter_window.buttonBox.accepted.connect(self.apply_filter)

        self.parent.current_filter = self.filter

        self.filter_window.exec()


class FilterSaturation(FilterBase):
    ui_name = "saturation_window"
    window_title = "Saturation"
    factor = 0

    @property
    def filter(self):
        return SaturationFilter(factor=self.factor / 1000)

    def show(self):
        super().show()
        # set the gaussian_blur_window settings values to the current settings
        self.filter_window.blur_slider.setValue(int(self.factor))
        self.filter_window.blur_slider.valueChanged.connect(
            lambda val: self.handle_blur_radius_slider_change(val))
        self.filter_window.blur_spinbox.setValue(self.factor / 1000.0)
        self.filter_window.blur_spinbox.valueChanged.connect(
            lambda val: self.handle_blur_radius_spinbox_change(val))

        # on ok button click, apply the filter
        self.filter_window.buttonBox.rejected.connect(self.cancel_filter)
        self.filter_window.buttonBox.accepted.connect(self.apply_filter)

        self.filter_window.exec()

    def handle_blur_radius_slider_change(self, val):
        print(val)
        self.factor = float(val)
        self.filter_window.blur_spinbox.setValue(val / 1000.0)
        self.parent.current_filter = self.filter
        self.canvas.update()

    def handle_blur_radius_spinbox_change(self, val):
        self.factor = val / 100.0
        self.filter_window.blur_slider.setValue(int(val * 1000.0))
        self.parent.current_filter = self.filter
        self.update_canvas()


class FilterColorBalance(FilterBase):
    ui_name = "color_balance"
    window_title = "Color Balance"

    def __init__(self, parent):
        super().__init__(parent)
        self.cyan_red = parent.settings_manager.settings.cyan_red
        self.magenta_green = parent.settings_manager.settings.magenta_green
        self.yellow_blue = parent.settings_manager.settings.yellow_blue

    @property
    def filter(self):
        return ColorBalanceFilter(
            cyan_red=self.cyan_red.get() / 1000,
            magenta_green=self.magenta_green.get() / 1000,
            yellow_blue=self.yellow_blue.get() / 1000
        )

    def show(self):
        super().show()

        self.cyan_red.set(0)
        self.magenta_green.set(0)
        self.yellow_blue.set(0)

        def update_filter():
            self.parent.current_filter = self.filter
            self.canvas.update()

        def color_balance_cyan_slider_change(val):
            self.filter_window.cyan_spinbox.setValue(val / 1000.0)
            self.filter_window.cyan_spinbox.update()
            update_filter()

        def color_balance_magenta_slider_change(val):
            self.filter_window.magenta_spinbox.setValue(val / 1000.0)
            self.filter_window.magenta_spinbox.update()
            update_filter()

        def color_balance_yellow_slider_change(val):
            self.filter_window.yellow_spinbox.setValue(val / 1000.0)
            self.filter_window.yellow_spinbox.update()
            update_filter()

        def color_balance_cyan_spinbox_change(val):
            self.filter_window.cyan_slider.setValue(int(val * 1000.0))
            self.filter_window.cyan_slider.update()
            update_filter()

        def color_balance_magenta_spinbox_change(val):
            self.filter_window.magenta_slider.setValue(int(val * 1000.0))
            self.filter_window.magenta_slider.update()
            update_filter()

        def color_balance_yellow_spinbox_change(val):
            self.filter_window.yellow_slider.setValue(int(val * 1000.0))
            self.filter_window.yellow_slider.update()
            update_filter()

        self.filter_window.cyan_slider.setValue(self.cyan_red.get())
        self.filter_window.cyan_slider.valueChanged.connect(lambda val: color_balance_cyan_slider_change(val))
        self.filter_window.cyan_spinbox.setValue(self.cyan_red.get() / 1000.0)
        self.filter_window.cyan_spinbox.valueChanged.connect(lambda val: color_balance_cyan_spinbox_change(val))

        self.filter_window.magenta_slider.setValue(self.magenta_green.get())
        self.filter_window.magenta_slider.valueChanged.connect(lambda val: color_balance_magenta_slider_change(val))
        self.filter_window.magenta_spinbox.setValue(self.magenta_green.get() / 1000.0)
        self.filter_window.magenta_spinbox.valueChanged.connect(lambda val: color_balance_magenta_spinbox_change(val))

        self.filter_window.yellow_slider.setValue(self.yellow_blue.get())
        self.filter_window.yellow_slider.valueChanged.connect(lambda val: color_balance_yellow_slider_change(val))
        self.filter_window.yellow_spinbox.setValue(self.yellow_blue.get() / 1000.0)
        self.filter_window.yellow_spinbox.valueChanged.connect(lambda val: color_balance_yellow_spinbox_change(val))

        # on ok button click, apply the filter
        self.filter_window.buttonBox.rejected.connect(self.cancel_filter)
        self.filter_window.buttonBox.accepted.connect(self.apply_filter)

        self.filter_window.exec()
