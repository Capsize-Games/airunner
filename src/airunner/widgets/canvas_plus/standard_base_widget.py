from PyQt6.QtGui import QPixmap

from airunner.utils import delete_image
from airunner.widgets.canvas_plus.canvas_base_widget import CanvasBaseWidget


class StandardBaseWidget(CanvasBaseWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.app.image_data.connect(self.handle_image_data)
        self.app.load_image.connect(self.load_image_from_path)
        self.ui.delete_confirmation.hide()

    def image_to_canvas(self):
        self.app.load_image_object.emit(self.image)

    def delete_image(self):
        self.ui.delete_confirmation.show()

    def confirm_delete(self):
        self._label.setPixmap(QPixmap())
        delete_image(self.image_path)
        self.ui.delete_confirmation.hide()

    def cancel_delete(self):
        self.ui.delete_confirmation.hide()
    
    def handle_image_data(self, data):
        pass

    def load_image_from_path(self, image_path):
        pass         

    def export_image(self):
        self.app.export_image(self.image)
