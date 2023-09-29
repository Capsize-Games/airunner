from PyQt6 import uic

from airunner.windows.deterministic_generation.templates.deterministic_generation_window_ui import \
    Ui_deterministic_generation_window
from airunner.utils import image_to_pixmap
from airunner.windows.base_window import BaseWindow
from functools import partial


class DeterministicGenerationWindow(BaseWindow):
    template_class_ = Ui_deterministic_generation_window
    is_modal = True
    images = []
    data = {}

    def __init__(self, *args, **kwargs):
        self.images = kwargs.get("images", self.images)
        self.data = kwargs.get("data")
        super().__init__(*args, **kwargs)

    def close_event(self, _event):
        self.app.close_deterministic_generation_window()
        self.ui.close()

    def initialize_window(self):
        self.add_image_widgets_to_canvas()
        self.ui.closeEvent = self.close_event
        # self.app.add_image_to_canvas_signal.connect(self.handle_add_image_to_canvas_signal)

    def add_image_widgets_to_canvas(self):
        if not self.images:
            return
        for index, image in enumerate(self.images):
            self.add_image_to_canvas(index, image)

    def add_image_to_canvas(self, index, image):
        widget = uic.loadUi("pyqt/deterministic_widget.ui")
        # insert image into template.thumbnail
        pixmap = image_to_pixmap(image.copy(), 200)
        widget.thumbnail.setPixmap(pixmap)
        widget.new_batch_button.clicked.connect(partial(self.new_batch, index))
        widget.to_canvas_button.clicked.connect(partial(self.to_canvas, index))
        # replace self.ui.widget_1 which is a QWidget with widget
        row = 0 if index < 2 else 1
        col = index % 2
        self.ui.gridLayout.addWidget(widget, row, col, 1, 1)

    def new_batch(self, index):
        self.app.new_batch(index, self.images[index], data=self.data)
        self.ui.close()

    def to_canvas(self, index):
        image = self.images[index]
        image = image.convert("RGBA")
        #self.app.canvas.add_image_to_canvas(image, QPoint(0, 0), QPoint(0, 0), use_outpaint=True)
        self.data["force_add_to_canvas"] = True
        self.data["options"]["outpaint_box_rect"] = self.app.active_rect
        self.app.canvas.update_image_canvas(self.data["action"], self.data, image)
        self.data["force_add_to_canvas"] = False

    def handle_add_image_to_canvas_signal(self, data):
        #data["add_image_to_canvas"] = False
        pass

    def update_images(self, images):
        self.images = images
        self.add_image_widgets_to_canvas()
