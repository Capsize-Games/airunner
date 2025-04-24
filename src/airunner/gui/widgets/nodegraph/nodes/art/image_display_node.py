from PySide6.QtWidgets import QLabel, QWidget, QVBoxLayout
from PySide6.QtGui import QPixmap, QImage
from PySide6.QtCore import Qt
from PIL.ImageQt import ImageQt

from airunner.gui.widgets.nodegraph.nodes.art.base_art_node import (
    BaseArtNode,
)
from airunner.handlers.stablediffusion.image_response import ImageResponse


# Wrapper widget required by NodeGraphQt
class ImageDisplayWidget(QWidget):
    def __init__(self, parent=None, name="image_display_widget"):
        super().__init__(parent)
        self._name = name
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.image_label = QLabel("No Image")
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setMinimumSize(128, 128)  # Set a minimum size
        layout.addWidget(self.image_label)

    # Implement the method expected by NodeGraphQt
    def widget(self):
        return self

    def get_name(self):
        return self._name

    def set_pixmap(self, pixmap):
        self.image_label.setPixmap(pixmap)

    def set_text(self, text):
        self.image_label.setText(text)

    def get_label_size(self):
        return self.image_label.size()

    # Add methods required by NodeGraphQt if needed
    def setDisabled(self, state):
        self.image_label.setDisabled(state)
        super().setDisabled(state)


class ImageDisplayNode(BaseArtNode):
    NODE_NAME = "Image Display"

    def __init__(self):
        super().__init__()

        # Input port for ImageResponse object
        self.add_input("image_response")

        # Create and add the custom wrapper widget to the node's view
        self.image_widget = ImageDisplayWidget(name="image_display")
        # Call add_widget on the view object
        if hasattr(self, "view") and hasattr(self.view, "add_widget"):
            self.view.add_widget(self.image_widget)
        else:
            print(
                f"Warning: Could not add widget to {self.NODE_NAME}. View or add_widget method not found."
            )

    def execute(self, input_data):
        image_response = self.get_input_data("image_response", input_data)

        if isinstance(image_response, ImageResponse) and image_response.images:
            # Display the first image from the list
            pil_image = image_response.images[0]
            if pil_image:
                # Convert PIL Image to QPixmap
                qimage = ImageQt(
                    pil_image.convert("RGBA")
                )  # Ensure RGBA for transparency
                pixmap = QPixmap.fromImage(qimage)
                # Scale pixmap to fit the label while maintaining aspect ratio
                scaled_pixmap = pixmap.scaled(
                    self.image_widget.get_label_size(),  # Use wrapper method
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation,
                )
                self.image_widget.set_pixmap(
                    scaled_pixmap
                )  # Use wrapper method
            else:
                self.image_widget.set_text(
                    "Image Data Empty"
                )  # Use wrapper method
        else:
            self.image_widget.set_text("Invalid Input")  # Use wrapper method

        # Return empty dict as this node primarily displays data
        # Execution flow is handled by the graph executor via exec ports
        return {}
