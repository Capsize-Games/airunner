from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QLabel
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QVBoxLayout
from PyQt6.QtWidgets import QTableWidgetItem
from PyQt6.QtWidgets import QApplication
from PyQt6.QtWidgets import QDialog
from PyQt6.QtGui import QImage

from PIL import Image

from airunner.widgets.base_widget import BaseWidget
from airunner.widgets.standard_image.templates.standard_image_widget_ui import Ui_standard_image_widget


class StandardImageWidget(BaseWidget):
    widget_class_ = Ui_standard_image_widget
    _pixmap = None
    _label = None
    _layout = None
    image_path = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.app.image_data.connect(self.handle_image_data)
        self.app.load_image.connect(self.load_image_from_path)
    
    def handle_image_data(self, data):
        self.load_image_from_object(data["image"])
    
    def load_image_from_path(self, image):
        image = Image.open(image)
        self.load_image_from_object(image)
    
    def load_image_from_object(self, image):
        if self.app.image_editor_tab_name == "Standard":
            self.set_pixmap(image=image)
    
    def set_pixmap(self, image_path=None, image=None):
        self.image_path = image_path
        self.image = image
        
        size = self.ui.image_frame.width()

        pixmap = self._pixmap
        if not pixmap:
            pixmap = QPixmap()
            self._pixmap = pixmap

        if image_path:
            pixmap.load(image_path)
        else:
            raw_data = image.tobytes("raw", "RGBA")
            qimage = QImage(
                raw_data, 
                image.size[0], 
                image.size[1], 
                QImage.Format.Format_RGBA8888
            )
            pixmap = QPixmap.fromImage(qimage)
        
        width = pixmap.width()
        height = pixmap.height()
        
        label = self._label
        if not label:
            label = QLabel(self.ui.image_frame)
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._label = label

        pixmap = pixmap.scaled(
            size, 
            size, 
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        label.setPixmap(pixmap)
        label.setFixedWidth(size)
        label.setFixedHeight(size)

        # on label click:
        label.mousePressEvent = self.handle_label_clicked
        label.setCursor(Qt.CursorShape.PointingHandCursor)
        
        layout = self._layout
        if not layout:
            layout = QVBoxLayout(self.ui.image_frame)
            layout.addWidget(label)        
            self._layout = layout
        
        # get the metadata from this image, load it as a png first
        # then load the metadata from the png
        self.clear_table_data()
        if image_path:
            image = Image.open(image_path)
            meta_data = image.info

            meta_data["width"] = width
            meta_data["height"] = height

            self.set_table_data(meta_data)
    
    def handle_label_clicked(self, event):
        # create a popup window and show the full size image in it
        self.dialog = QDialog()
        self.dialog.setWindowTitle("Image preview")
        layout = QVBoxLayout(self.dialog)
        self.dialog.setLayout(layout)

        if self.image_path:
            pixmap = QPixmap(self.image_path)
        elif self.image:
            raw_data = self.image.tobytes("raw", "RGBA")
            qimage = QImage(
                raw_data, 
                self.image.size[0], 
                self.image.size[1], 
                QImage.Format.Format_RGBA8888
            )
            pixmap = QPixmap.fromImage(qimage)
        label = QLabel()
        label.setPixmap(pixmap)
        layout.addWidget(label)
        self.dialog.show()
    
    def set_table_data(self, data):
        for k, v in data.items():
            self.ui.tableWidget.insertRow(self.ui.tableWidget.rowCount())
            self.ui.tableWidget.setItem(self.ui.tableWidget.rowCount()-1, 0, QTableWidgetItem(str(k)))
            self.ui.tableWidget.setItem(self.ui.tableWidget.rowCount()-1, 1, QTableWidgetItem(str(v)))
        self.ui.tableWidget.update()
        QApplication.processEvents()
        
        self.ui.tableWidget.resizeColumnsToContents()
        self.ui.tableWidget.resizeRowsToContents()

    def clear_table_data(self):
        self.ui.tableWidget.clearContents()
        self.ui.tableWidget.setRowCount(0)