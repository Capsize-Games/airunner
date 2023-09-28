import os
from PyQt6 import QtGui

from airunner.pyqt.widgets.base_widget import BaseWidget
from airunner.pyqt.widgets.layers.layer_ui import Ui_LayerWidget
from airunner.themes import Themes
from airunner.utils import image_to_pixmap


class LayerWidget(BaseWidget):
    widget_class_ = Ui_LayerWidget

    def __init__(self, *args, **kwargs):
        self.data = kwargs.pop("data", None)
        super().__init__(*args, **kwargs)
        self.set_icon()
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.set_thumbnail()
        self.set_stylesheet()

    def set_stylesheet(self):
        super().set_stylesheet()
        self.setStyleSheet(Themes().css("layer_widget"))
        self.ui.thumbnail_label.setStyleSheet(Themes().css("thumbnail_label"))
        self.ui.visible_button.setStyleSheet(Themes().css("border-light"))

    def set_thumbnail(self):
        image = self.data.image_data.image
        if image:
            thumbnail = image.copy()
            pixmap = image_to_pixmap(thumbnail, 32)
            self.ui.thumbnail_label.setPixmap(pixmap)
        else:
            self.ui.thumbnail_label.width = 32
            self.ui.thumbnail_label.height = 32
            # clear the thumbnail
            self.ui.thumbnail_label.setPixmap(QtGui.QPixmap())

    def set_icon(self):
        is_dark = self.settings_manager.dark_mode_enabled
        filename = "src/icons/010-view" if self.data.visible else "src/icons/009-hide"
        self.ui.visible_button.setIcon(QtGui.QIcon(
            os.path.join(f"{filename}{'-light' if is_dark else ''}.png")
        ))
