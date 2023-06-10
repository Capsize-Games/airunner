from PIL import Image
from PyQt6.QtCore import QPoint


class ImageData:
    def __init__(self, position: QPoint, image: Image):
        self.position = position
        self.image = image
        self.opacity = opacity * 255
