from PIL import ImageFilter

from airunner.windows.main.settings_mixin import SettingsMixin


class BaseFilter(ImageFilter.Filter, SettingsMixin):
    def __init__(self, **kwargs):
        super().__init__()
        self.image = None
        self.image_id = None

        for k,v in kwargs.items():
            setattr(self, k, v)

    def filter(self, image):
        do_reset = False
        if not self.image_id or self.image_id != id(image):
            self.image_id = id(image)
            self.image = image
            do_reset = True
        res = self.apply_filter(image, do_reset)
        return res

    def apply_filter(self, image, do_reset=False):
        """
        Override this function
        :param image:
        :param do_reset:
        :return:
        """
        raise NotImplementedError()
