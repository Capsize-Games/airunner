from PyQt6.uic.properties import QtGui

from airunner.utils import image_to_pixmap
from airunner.widgets.base_widget import BaseWidget
from airunner.widgets.layers.templates.layer_image_widget_ui import Ui_layer_image_widget
from airunner.data.session_scope import session_scope


class LayerImageWidget(BaseWidget):
    widget_class_ = Ui_layer_image_widget

    def __init__(self, layer_image_data):
        super().__init__()
        self.layer_image_data = layer_image_data
        #self.ui.opacity_slider_widget.setProperty("current_value", self.layer_image_data.opacity)
        self.set_thumbnail()

    def action_clicked_button_toggle_image_visibility(self, value):
        with session_scope() as session:
            session.add(self.layer_image_data)
            self.layer_image_data.visible = value
            self.app.settings_manager.save_and_emit(
                "layer_image_data.visible",
                value
            )

    def set_thumbnail(self):
        image = self.layer_image_data.image
        if image:
            thumbnail = image.copy()
            pixmap = image_to_pixmap(thumbnail, 32)
            self.ui.thumbnail.setPixmap(pixmap)
        else:
            self.ui.thumbnail.width = 32
            self.ui.thumbnail.height = 32
            self.ui.thumbnail.setPixmap(QtGui.QPixmap())
