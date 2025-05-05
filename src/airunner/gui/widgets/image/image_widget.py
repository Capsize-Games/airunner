import os
import json

from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QLabel
from PySide6.QtCore import Qt
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QMenu
from PySide6.QtWidgets import QMessageBox
from PIL import Image
from PIL.ImageQt import ImageQt
from airunner.enums import SignalCode, CanvasToolName
from airunner.utils.image import load_metadata_from_image, delete_image
from airunner.gui.widgets.base_widget import BaseWidget
from airunner.gui.widgets.image.templates.image_widget_ui import (
    Ui_image_widget,
)
from PySide6.QtGui import QDrag
from PySide6.QtCore import QMimeData
from PySide6.QtCore import QByteArray


class ImageWidget(BaseWidget):
    widget_class_ = Ui_image_widget
    image_path = None
    meta_data = {}
    image_width = 0
    image_height = 0
    clicked = Signal()
    pixmap = None

    def __init__(self, *args, **kwargs):
        self.is_thumbnail = kwargs.pop("is_thumbnail", False)
        super().__init__(*args, **kwargs)

    def set_image(self, image_path):
        size = self.ui.image_frame.width()
        self.image_path = image_path

        self.load_meta_data(image_path)

        # Create a QPixmap object

        if isinstance(self.image_path, Image.Image):
            qimage = ImageQt(
                self.image_path
            )  # Convert the PngImageFile to a QImage
            pixmap = QPixmap.fromImage(
                qimage
            )  # Create a QPixmap from the QImage
        else:
            # check if thumbnail exists at path
            # if not, create it
            path = self.image_path + ".thumbnail.png"
            if not os.path.exists(path):
                image = Image.open(self.image_path)
                try:
                    image.thumbnail((size, size))
                except OSError:
                    pass
                try:
                    image.save(path)
                except OSError:
                    pass
            if self.is_thumbnail:
                pixmap = QPixmap(path)
            else:
                pixmap = QPixmap(self.image_path)
        self.pixmap = pixmap

        # set width and height
        self.image_width = pixmap.width()
        self.image_height = pixmap.height()

        # Create a QLabel object
        label = QLabel(self.ui.image_frame)

        # set width and height of label to size
        label.setFixedWidth(size)
        label.setFixedHeight(size)
        label.mousePressEvent = self.handle_label_clicked
        label.setCursor(Qt.CursorShape.PointingHandCursor)

        # Set the pixmap to the label
        label.setPixmap(pixmap)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)

    def handle_label_clicked(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            drag = QDrag(self)
            mime_data = QMimeData()

            # Load the image metadata
            self.load_meta_data(self.image_path)

            # Convert the metadata to a JSON string
            meta_data = self.meta_data.copy()
            meta_data["path"] = self.image_path
            meta_data_str = json.dumps(meta_data)

            # Encode the JSON string to bytes
            meta_data_bytes = meta_data_str.encode()

            # Set the metadata as additional data in the QMimeData object
            mime_data.setData(
                "application/x-qt-image-metadata", QByteArray(meta_data_bytes)
            )

            drag.setMimeData(mime_data)

            # Set a pixmap for the drag operation
            pixmap = QPixmap(self.image_path)

            # Scale the pixmap to no larger than 128x128 while maintaining aspect ratio
            pixmap = pixmap.scaled(
                128, 128, Qt.AspectRatioMode.KeepAspectRatio
            )

            drag.setPixmap(pixmap)

            # Execute the drag operation
            drag.exec(Qt.DropAction.MoveAction)
        elif event.button() == Qt.MouseButton.RightButton:
            # self.send_image_to_grid()
            self.display_image_menu(event)

    def display_image_menu(self, event):
        context_menu = QMenu(self)

        view_action = context_menu.addAction("View")
        edit_action = context_menu.addAction("Edit")
        delete_action = context_menu.addAction("Delete")

        # display image in a window
        view_action.triggered.connect(lambda: self.view_image())
        edit_action.triggered.connect(lambda: self.send_image_to_grid())
        delete_action.triggered.connect(lambda: self.delete_image())

        global_position = self.mapToGlobal(event.pos())
        context_menu.exec(global_position)

    def load_meta_data(self, image_path):
        # load the png metadata from image_path
        # check if image_path is Image
        if isinstance(image_path, Image.Image):
            image = image_path
        else:
            with open(image_path, "rb") as image_file:
                image = Image.open(image_file)

        if image:
            self.meta_data = load_metadata_from_image(image)

    def send_image_to_grid(self):
        self.api.art.canvas.image_from_path(self.image_path)

    def view_image(self):
        from PySide6.QtWidgets import (
            QGraphicsView,
            QGraphicsScene,
            QDialog,
            QVBoxLayout,
        )
        from PySide6.QtGui import QPixmap
        from PySide6.QtCore import Qt
        from PySide6.QtGui import QPainter

        # Open the image
        image = QPixmap(self.image_path)

        # Create a QGraphicsScene and add the image to it
        scene = QGraphicsScene()
        scene.addPixmap(image)

        # Create a QGraphicsView and set its scene to be the one we just created
        view = QGraphicsView(scene)

        # Enable dragging and using the scroll wheel to zoom
        view.setRenderHint(QPainter.RenderHint.Antialiasing)
        view.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        view.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        view.setOptimizationFlags(
            QGraphicsView.OptimizationFlag.DontAdjustForAntialiasing
            | QGraphicsView.OptimizationFlag.DontSavePainterState
        )
        view.setViewportUpdateMode(
            QGraphicsView.ViewportUpdateMode.FullViewportUpdate
        )
        view.setTransformationAnchor(
            QGraphicsView.ViewportAnchor.AnchorUnderMouse
        )
        view.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        view.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        view.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        view.setInteractive(True)
        view.setMouseTracking(True)
        view.setRenderHints(
            QPainter.RenderHint.Antialiasing
            | QPainter.RenderHint.SmoothPixmapTransform
            | QPainter.RenderHint.TextAntialiasing
        )

        # Create a layout and add the QGraphicsView to it
        layout = QVBoxLayout()
        layout.addWidget(view)

        # Create a QDialog, set its layout and show it
        dialog = QDialog()
        dialog.setLayout(layout)
        dialog.exec()

    def delete_image(self):
        confirm_dialog = QMessageBox()
        confirm_dialog.setIcon(QMessageBox.Icon.Warning)
        confirm_dialog.setText("Are you sure you want to delete this image?")
        confirm_dialog.setWindowTitle("Confirm Delete")
        confirm_dialog.setStandardButtons(
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        result = confirm_dialog.exec()
        if result == QMessageBox.StandardButton.Yes:
            self.confirm_delete()
        else:
            self.cancel_delete()

    def confirm_delete(self):
        delete_image(self.image_path)
        delete_image(self.image_path + ".thumbnail.png")
        self.deleteLater()

    def cancel_delete(self):
        pass
