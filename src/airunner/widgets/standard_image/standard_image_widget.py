from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QLabel
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QVBoxLayout
from PyQt6.QtWidgets import QTableWidgetItem
from PyQt6.QtWidgets import QApplication
from PyQt6.QtWidgets import QDialog

from PIL import Image

from airunner.widgets.base_widget import BaseWidget
from airunner.widgets.standard_image.templates.standard_image_widget_ui import Ui_standard_image_widget


class StandardImageWidget(BaseWidget):
    widget_class_ = Ui_standard_image_widget
    _pixmap = None
    _label = None
    _layout = None
    image_path = None
    
    def set_pixmap(self, image_path):
        self.image_path = image_path
        size = self.ui.image_frame.width()

        pixmap = self._pixmap
        if not pixmap:
            pixmap = QPixmap(image_path)
            self._pixmap = pixmap
        else:
            pixmap.load(image_path)
        
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
        image = Image.open(image_path)
        meta_data = image.info

        meta_data["width"] = width
        meta_data["height"] = height

        self.clear_table_data()
        self.set_table_data(meta_data)
    
    def handle_label_clicked(self, event):
        # create a popup window and show the full size image in it
        self.dialog = QDialog()
        self.dialog.setWindowTitle("Image preview")
        layout = QVBoxLayout(self.dialog)
        self.dialog.setLayout(layout)
        pixmap = QPixmap(self.image_path)
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