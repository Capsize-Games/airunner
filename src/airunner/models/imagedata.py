from PIL import Image
from PyQt6.QtCore import QPoint


class ImageData:
    @property
    def image(self):
        return self._image

    @image.setter
    def image(self, value):
        self._image = value
        if self._image and self.backup is None:
            r, g, b, a = self._image.split()
            self.backup = a

    def __init__(
        self,
        position: QPoint,
        image: Image,
        opacity: float,
        mask: Image = None,
        image_pivot_point: QPoint = QPoint(0, 0),
        image_root_point: QPoint = QPoint(0, 0)
    ):
        self.image_pivot_point = image_pivot_point
        self.image_root_point = image_root_point
        self._image = None
        self.mask_mode_active = False
        self.backup = None
        self.position = position
        self.image = image
        self.mask = mask
        self.opacity = opacity * 255
