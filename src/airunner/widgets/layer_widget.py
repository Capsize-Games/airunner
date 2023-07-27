import os
from PyQt6 import QtGui
from airunner.utils import image_to_pixmap
from airunner.widgets.base_widget import BaseWidget


class LayerWidget(BaseWidget):
    name = "layer"

    def __init__(self, *args, **kwargs):
        self.data = kwargs.pop("data", None)
        super().__init__(*args, **kwargs)
        self.set_icon()
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.set_thumbnail()
        self.set_stylesheet()

    def set_stylesheet(self):
        super().set_stylesheet()
        self.setStyleSheet(self.app.css("layer_widget"))
        self.thumbnail_label.setStyleSheet(self.app.css("thumbnail_label"))
        self.visible_button.setStyleSheet(self.app.css("border-light"))

    def set_thumbnail(self):
        image = self.data.image_data.image
        if image:
            thumbnail = image.copy()
            pixmap = image_to_pixmap(thumbnail, 32)
            self.thumbnail_label.setPixmap(pixmap)
        else:
            self.thumbnail_label.width = 32
            self.thumbnail_label.height = 32
            # clear the thumbnail
            self.thumbnail_label.setPixmap(QtGui.QPixmap())

    def set_icon(self):
        is_dark = self.app.settings_manager.settings.dark_mode_enabled.get()
        filename = "src/icons/010-view" if self.data.visible else "src/icons/009-hide"
        self.visible_button.setIcon(QtGui.QIcon(
            os.path.join(f"{filename}{'-light' if is_dark else ''}.png")
        ))