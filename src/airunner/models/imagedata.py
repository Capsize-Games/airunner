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

    def __init__(self, position: QPoint, image: Image, opacity: float):
        self.backup = None
        self.position = position
        self.image = image
        self.opacity = opacity * 255
