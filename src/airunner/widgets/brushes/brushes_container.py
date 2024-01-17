import io
from io import BytesIO
import json
import base64
from PIL import Image

from PyQt6.QtWidgets import QInputDialog
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import QBuffer
from PyQt6.QtWidgets import QMenu

from airunner.widgets.base_widget import BaseWidget
from airunner.widgets.image.image_widget import BrushImageWidget
from airunner.widgets.qflowlayout.q_flow_layout import QFlowLayout


class BrushesContainer(BaseWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Enable the widget to accept drops
        self.setAcceptDrops(True)

        # Create a layout to manage the widgets
        self.layout = QFlowLayout()
        self.setLayout(self.layout)

        self.load_brushes()

    def dragEnterEvent(self, event):
        # Accept the drag enter event if the data is text
        event.acceptProposedAction()
    
    def save_brush(self, brush_name, thumbnail: QPixmap, meta_data):
        # Convert QPixmap to QImage
        image = thumbnail.toImage()

        # Convert QImage to raw bytes
        from PyQt6.QtCore import QIODevice  # Import the QIODevice class

        buffer = QBuffer()
        buffer.open(QIODevice.OpenModeFlag.ReadWrite)  # Use QIODevice.OpenModeFlag.ReadWrite
        image.save(buffer, "PNG")

        # Use PIL to open the image from raw bytes
        with Image.open(io.BytesIO(buffer.data())) as img:
            # Convert the image to RGB
            img = img.convert('RGB')

            # Create a BytesIO object
            buffer = BytesIO()

            # Save the image to the BytesIO object
            img.save(buffer, format='PNG')

            # Get the bytes value of the image
            img_bytes = buffer.getvalue()

            # Convert the bytes to base64
            img_base64 = base64.b64encode(img_bytes).decode()

        # Create a new Brush entry
        settings = self.app.settings
        brush = dict(
            name=brush_name, 
            thumbnail=img_base64
        )
        settings["presets"].append(brush)
        self.settings = settings
        return brush
    
    selected_brushes = []

    def activate_brush(self, clicked_widget, brush, multiple):
        if clicked_widget in self.selected_brushes:
            if len(self.selected_brushes) == 1:
                self.selected_brushes.remove(clicked_widget)
                clicked_widget.setStyleSheet("")
            else:
                for widget in self.selected_brushes:
                    if not multiple:
                        if widget is not clicked_widget:
                            self.selected_brushes.remove(widget)
                            widget.setStyleSheet("")
                            break
                    else:
                        self.selected_brushes.remove(widget)
                        widget.setStyleSheet("")
            print("TODO: save this?")
            return

        for widget in self.selected_brushes:
            try:
                widget.setStyleSheet("")
            except RuntimeError:
                pass
        
        if not multiple:
            self.selected_brushes = [clicked_widget]
        else:
            self.selected_brushes.append(clicked_widget)
        
        if len(self.selected_brushes) > 2:
            self.selected_brushes = self.selected_brushes[1:]
        
        for widget in self.selected_brushes:
            widget.setStyleSheet(f"""
                border: 2px solid #ff0000;
            """)
    
    def display_brush_menu(self, event, widget, brush):
        context_menu = QMenu(self)

        delete_action = context_menu.addAction("Delete brush")
        delete_action.triggered.connect(lambda: self.delete_brush(widget, brush))

        global_position = self.mapToGlobal(event.pos())
        context_menu.exec(global_position)

    def delete_brush(self, widget, brush):
        settings = self.app.settings
        for index, brush_data in enumerate(settings["presets"]):
            if brush["name"] == brush_data["name"]:
                del settings["presets"][index]
                break
        self.settings = settings
        widget.deleteLater()
    
    def create_and_add_widget(self, image_source, is_base64=False, brush: dict=None):
        widget = BrushImageWidget(self, container=self, brush=brush)

        if is_base64:
            # Convert the base64 image back to bytes
            img_bytes = base64.b64decode(image_source)
            
            # Create a BytesIO object from the bytes
            buffer = BytesIO(img_bytes)
            
            # Open the image file
            img = Image.open(buffer)
        else:
            img = image_source
        # Set the image to the widget
        widget.set_image(img)
        
        # Add the widget to the layout
        self.layout.addWidget(widget)

        return widget

    def dropEvent(self, event):
        # Get the metadata from the event's mime data
        meta_data_bytes = event.mimeData().data("application/x-qt-image-metadata")

        # Decode the bytes to a string
        meta_data_str = bytes(meta_data_bytes).decode()

        # Parse the JSON string to a dictionary
        meta_data = json.loads(meta_data_str)

        image_path = meta_data["path"]

        # Create an instance of the widget with the image path
        widget = self.create_and_add_widget(image_path)

        # Show a popup window asking the user to name the brush
        brush_name, ok = QInputDialog.getText(self, 'Name the preset', 'Enter preset name:')

        # If the user cancels the dialog, remove the widget from the layout
        if not ok or not brush_name:
            widget.deleteLater()
        else:
            # Save the brush name, thumbnail, and metadata to the database
            widget._brush = self.save_brush(brush_name, widget.pixmap, meta_data)
            

        event.acceptProposedAction()

    def load_brushes(self):
        for brush in self.app.settings["presets"]:
            self.create_and_add_widget(
                brush["thumbnail"], 
                is_base64=True, 
                brush=brush
            )
