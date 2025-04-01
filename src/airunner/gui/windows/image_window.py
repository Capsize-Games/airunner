import numpy as np
from PIL import Image
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget
from PySide6.QtGui import QPixmap, QImage
from PySide6.QtCore import Qt


class ImageWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Video Feed')
        self.layout = QVBoxLayout()
        self.label = QLabel()
        self.layout.addWidget(self.label)
        self.setLayout(self.layout)

    def update_image(self, image: Image):
        # Ensure the image is in RGB mode
        image = image.convert("RGB")

        # Convert PIL Image to numpy array
        image_array = np.array(image)

        # Convert numpy array to QImage
        qim = QImage(
            image_array.data,
            image.width,
            image.height,
            image.width * 3,
            QImage.Format.Format_RGB888
        )
        pixmap = QPixmap.fromImage(qim)
        self.label.setPixmap(pixmap)
        self.show()
