from functools import partial

from PyQt6 import QtGui

from airunner.widgets.base_widget import BaseWidget
from airunner.widgets.layers.templates.layer_ui import Ui_LayerWidget
from airunner.utils import image_to_pixmap


class LayerWidget(BaseWidget):
    widget_class_ = Ui_LayerWidget
    layer_data = None

    def __init__(self, *args, **kwargs):
        self.layer_data = kwargs.pop("layer_data", None)
        self.layer_index = kwargs.pop("layer_index", None)
        super().__init__(*args, **kwargs)
        self.set_thumbnail()

        # listen for click on entire widget
        self.ui.mousePressEvent = partial(self.action_clicked, self.layer_data, self.layer_index)
        self.ui.layer_name.setText(self.layer_data.name)

    def action_clicked(self):
        print("select layer")

    def action_clicked_button_toggle_layer_visibility(self):
        pass

    def set_thumbnail(self):
        image = self.layer_data.image_data.image
        if image:
            thumbnail = image.copy()
            pixmap = image_to_pixmap(thumbnail, 32)
            self.ui.thumbnail.setPixmap(pixmap)
        else:
            self.ui.thumbnail.width = 32
            self.ui.thumbnail.height = 32
            self.ui.thumbnail.setPixmap(QtGui.QPixmap())
