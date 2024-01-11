from PyQt6.QtGui import QPixmap

from airunner.utils import delete_image
from airunner.widgets.canvas_plus.canvas_base_widget import CanvasBaseWidget


class StandardBaseWidget(CanvasBaseWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.app.image_data.connect(self.handle_image_data)
        self.app.load_image.connect(self.load_image_from_path)

    def handle_image_data(self, data):
        print("standard base widget handle image data")
        pass

    def load_image_from_path(self, image_path):
        pass
