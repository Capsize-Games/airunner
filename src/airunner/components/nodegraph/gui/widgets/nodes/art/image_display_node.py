from PySide6.QtWidgets import QLabel
from PySide6.QtGui import QPixmap
from PySide6.QtCore import Qt
from PIL.ImageQt import ImageQt
from airunner.vendor.nodegraphqt import NodeBaseWidget

from airunner.components.nodegraph.gui.widgets.nodes.art.base_art_node import (
    BaseArtNode,
)
from airunner.components.art.managers.stablediffusion.image_response import (
    ImageResponse,
)


class ImageDisplayWidget(NodeBaseWidget):
    """
    Widget to display images in a node graph.
    Following the pattern of TextEditNode which works correctly in airunner.vendor.nodegraphqt.
    """

    def __init__(
        self, parent=None, name="image_display", label="Image Display"
    ):
        super().__init__(parent, name, label)
        # Create the QLabel widget that will actually display the image
        self.image_label = QLabel("No Image")
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setMinimumSize(1024, 1024)
        # This is the key part - set the QLabel as the custom widget
        self.set_custom_widget(self.image_label)
        # Store the last value for get_value() to return
        self._value = None

    def get_value(self):
        """Return the stored value, which might be None for display-only widgets"""
        return self._value

    def set_value(self, value=None):
        """
        Required method for airunner.vendor.nodegraphqt to restore widget state.
        For image display, we just store the value and emit change signal.
        """
        self._value = value
        # Use _name instead of name for the signal
        self.value_changed.emit(self._name, value)

    def get_label_widget(self):
        """Get the actual QLabel widget inside the NodeGroupBox wrapper"""
        if (
            self.widget()
            and hasattr(self.widget(), "layout")
            and self.widget().layout()
        ):
            # NodeGroupBox contains our actual widget in its layout at index 0
            layout = self.widget().layout()
            if layout.count() > 0:
                item = layout.itemAt(0)
                if item and item.widget():
                    return item.widget()
        return None

    def get_label_size(self):
        return self.image_label.size()

    # Add methods required by airunner.vendor.nodegraphqt if needed
    def setDisabled(self, state):
        self.image_label.setDisabled(state)
        super().setDisabled(state)

    def set_pixmap(self, pixmap):
        """Set the pixmap to display"""
        self.image_label.setPixmap(pixmap)

    def set_text(self, text):
        """Set text to display when no image is available"""
        self.image_label.setText(text)


class ImageDisplayNode(BaseArtNode):
    NODE_NAME = "Image Display"

    def __init__(self):
        super().__init__()

        # Input port for ImageResponse object
        self.add_input("image_response")
        self.add_output("image")

        # Create and add the custom wrapper widget to the node using airunner.vendor.nodegraphqt's API
        self.image_widget = ImageDisplayWidget(self.view, name="image_display")
        self.add_custom_widget(self.image_widget)

    def execute(self, input_data):
        image_response = self.get_input_data("image_response", input_data)

        pil_image = (
            image_response.images[0]
            if (
                image_response is not None
                and isinstance(image_response, ImageResponse)
                and len(image_response.images) > 0
            )
            else None
        )

        if pil_image:
            qimage = ImageQt(pil_image.convert("RGBA"))
            pixmap = QPixmap.fromImage(qimage)
            scaled_pixmap = pixmap.scaled(
                self.image_widget.widget().size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self.image_widget.set_pixmap(scaled_pixmap)
        else:
            self.image_widget.set_text("Invalid or Empty Image")

        if pil_image:
            return {"image": pil_image}
