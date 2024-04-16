from PySide6.QtWidgets import (
    QVBoxLayout,
    QLabel,
    QSpinBox,
    QPushButton
)
from PySide6.QtGui import QPixmap
from threading import Lock
from airunner.enums import SignalCode
from airunner.widgets.base_widget import BaseWidget


class BlenderViewportWidget(BaseWidget):
    def __init__(self):
        super().__init__()
        self.setup_ui()
        self.image_lock = Lock()
        self.camera_lock = Lock()  # Lock for controlling camera size

        self.register(SignalCode.VIEWPORT_IMAGE, self.update_viewport_image)

    def setup_ui(self):
        layout = QVBoxLayout()
        self.image_label = QLabel()
        layout.addWidget(self.image_label)

        # Add UI elements for changing viewport size
        self.size_spinbox = QSpinBox()
        self.size_spinbox.setRange(1, 1000)  # Adjust range as needed
        layout.addWidget(self.size_spinbox)

        # Button to apply viewport size change
        self.apply_button = QPushButton("Apply Size Change")
        self.apply_button.clicked.connect(self.apply_size_change)
        layout.addWidget(self.apply_button)

        self.setLayout(layout)

    def apply_size_change(self):
        new_size = self.size_spinbox.value()
        with self.camera_lock:  # Acquire lock before making API call to Blender
            # Call function to update Blender camera size
            self.update_blender_camera_size(new_size)

    def update_viewport_image(self, image):
        with self.image_lock:
            pixmap = QPixmap.fromImage(image)
            self.image_label.setPixmap(pixmap)

    def update_blender_camera_size(self, new_size):
        # Your code to update Blender camera size through an API call
        # This could involve sending a message to Blender or invoking a script
        pass
