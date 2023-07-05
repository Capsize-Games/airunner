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
        self.setStyleSheet("""
        font-size: 9pt;
        """)
        self.thumbnail_label.setStyleSheet("border: 1px solid #121212; width: 32px; height: 32px;")
        self.set_thumbnail()
        self.visible_button.setStyleSheet("border: 1px solid #333333")

    def set_thumbnail(self):
        image = self.data.image_data.image
        if image:
            thumbnail = image.copy()
            pixmap = image_to_pixmap(thumbnail, 32)
            self.thumbnail_label.setPixmap(pixmap)
        else:
            self.thumbnail_label.width = 32
            self.thumbnail_label.height = 32

    def set_icon(self):
        is_dark = self.app.settings_manager.settings.dark_mode_enabled.get()
        filename = "src/icons/010-view" if self.data.visible else "src/icons/009-hide"
        self.visible_button.setIcon(QtGui.QIcon(
            os.path.join(f"{filename}{'-light' if is_dark else ''}.png")
        ))