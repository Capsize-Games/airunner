import os

from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QLabel
from PyQt6.QtCore import Qt

from airunner.widgets.base_widget import BaseWidget
from airunner.widgets.image.templates.image_widget_ui import Ui_image_widget


class ImageWidget(BaseWidget):
    widget_class_ = Ui_image_widget
    image_path = None

    def set_image(self, image_path):
        size = 256
        self.image_path = image_path

        # Create a QPixmap object
        pixmap = QPixmap(self.image_path)
        pixmap = pixmap.scaled(size, size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)

        # Create a QLabel object
        label = QLabel(self.ui.image_frame)

        # set width and height of label to size
        label.setFixedWidth(size)
        label.setFixedHeight(size)

        # Set the pixmap to the label
        label.setPixmap(pixmap)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)

    def delete_image(self):
        if not self.image_path:
            return
        os.remove(self.image_path)
        # delete this widget
        self.deleteLater()
