from PySide6.QtWidgets import QLabel
from PySide6.QtGui import QPixmap, QImage
from PySide6.QtCore import Qt
from PIL.ImageQt import ImageQt

from airunner.gui.widgets.nodegraph.nodes.base_workflow_node import (
    BaseWorkflowNode,
)
from airunner.handlers.stablediffusion.image_response import ImageResponse


class ImageDisplayNode(BaseWorkflowNode):
    NODE_NAME = "Image Display"
    __identifier__ = "airunner.workflow.nodes"  # Ensure consistent identifier

    def __init__(self):
        super().__init__()

        # Input port for ImageResponse object
        self.add_input("image_response")  # Remove data_type argument

        # Output port (optional, could pass through the response or other data)
        # self.add_output("output_data") # Keep exec_out from base class

        # UI Element to display the image
        self.image_label = QLabel("No Image")
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setMinimumSize(128, 128)  # Set a minimum size
        self.add_widget(
            self.image_label
        )  # Use the base class method if available, or directly add

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
                    self.image_label.size(),
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation,
                )
                self.image_label.setPixmap(scaled_pixmap)
            else:
                self.image_label.setText("Image Data Empty")
        else:
            self.image_label.setText("Invalid Input")

        # Return empty dict as this node primarily displays data
        # Execution flow is handled by the graph executor via exec ports
        return {}

    # Override add_widget if BaseWorkflowNode doesn't have it
    # Assuming BaseNode or a parent provides a way to add widgets to the node's view
    def add_widget(self, widget):
        if hasattr(
            self.view, "add_widget"
        ):  # Check if the view object has add_widget
            self.view.add_widget(widget)
        else:
            # Fallback or alternative method if direct view manipulation is needed
            # This might depend on the specifics of NodeGraphQt's node view structure
            print(
                f"Warning: Node {self.name()} cannot directly add widget. View object lacks 'add_widget'."
            )
            # You might need to access a layout within the view or use a specific method provided by the library.
