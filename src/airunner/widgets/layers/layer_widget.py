from functools import partial

from PyQt6 import QtGui
from PyQt6.QtCore import Qt, QPoint

from airunner.widgets.base_widget import BaseWidget
from airunner.widgets.layers.layer_image_widget import LayerImageWidget
from airunner.widgets.layers.templates.layer_ui import Ui_LayerWidget
from airunner.utils import image_to_pixmap


class LayerWidget(BaseWidget):
    widget_class_ = Ui_LayerWidget
    layer_data = None
    offset = QPoint(0, 0)
    _previous_pos = None

    def __init__(self, *args, **kwargs):
        self.layer_container = kwargs.pop("layer_container", None)
        self.layer_data = kwargs.pop("layer_data", None)
        self.layer_index = kwargs.pop("layer_index", None)
        self.layer_data.layer_widget = self
        super().__init__(*args, **kwargs)
        self.set_thumbnail()

        # listen for click on entire widget
        self.ui.mousePressEvent = partial(self.action_clicked, self.layer_data, self.layer_index)
        self.ui.layer_name.setText(self.layer_data.name)

    def reset_position(self):
        self._previous_pos = None

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.offset = event.pos()

    def mouseMoveEvent(self, event):
        if not self._previous_pos:
            self._previous_pos = self.pos()
        if event.buttons() == Qt.MouseButton.LeftButton:
            self.layer_container.handle_layer_click(self, self.layer_index, event)
            self.move(self.pos() + event.pos() - self.offset)

    def mouseReleaseEvent(self, event):
        if self._previous_pos:
            self.move(self._previous_pos)

    def action_clicked(self):
        print("select layer")

    def action_clicked_button_toggle_layer_visibility(self, val):
        self.layer_data.hidden = not val
        self.settings_manager.save_and_emit(
            "layer_data.hidden",
            self.layer_data.hidden
        )

    def set_thumbnail(self):
        image = self.layer_data.image
        if image:
            thumbnail = image.copy()
            pixmap = image_to_pixmap(thumbnail, 32)
            self.ui.thumbnail.setPixmap(pixmap)
        else:
            self.ui.thumbnail.width = 32
            self.ui.thumbnail.height = 32
            self.ui.thumbnail.setPixmap(QtGui.QPixmap())
