import os

from PyQt6.QtCore import QFileSystemWatcher
from PyQt6.QtCore import QPoint
from PyQt6.QtCore import QRect
from PyQt6.QtCore import QSize
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QLayout
from PyQt6.QtWidgets import QSizePolicy


from airunner.widgets.base_widget import BaseWidget
from airunner.widgets.image.image_widget import ImageWidget
from airunner.widgets.image.templates.image_panel_widget_ui import Ui_image_panel_widget


class QFlowLayout(QLayout):
    def __init__(self, parent=None, margin=0, hSpacing=-1, vSpacing=-1):
        super(QFlowLayout, self).__init__(parent)

        if parent is not None:
            self.setContentsMargins(margin, margin, margin, margin)

        self.margin = margin
        self.hSpacing = hSpacing
        self.vSpacing = vSpacing

        self.itemList = []

    def __del__(self):
        item = self.takeAt(0)
        while item:
            item = self.takeAt(0)

    def addItem(self, item):
        self.itemList.append(item)

    def horizontalSpacing(self):
        if self.hSpacing >= 0:
            return self.hSpacing
        else:
            return self.spacing()

    def verticalSpacing(self):
        if self.vSpacing >= 0:
            return self.vSpacing
        else:
            return self.spacing()

    def count(self):
        return len(self.itemList)

    def itemAt(self, index):
        if 0 <= index < len(self.itemList):
            return self.itemList[index]

        return None

    def takeAt(self, index):
        if 0 <= index < len(self.itemList):
            return self.itemList.pop(index)

        return None

    def expandingDirections(self):
        return Qt.Orientation(0)

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        height = self.doLayout(QRect(0, 0, width, 0), True)
        return height

    def setGeometry(self, rect):
        super(QFlowLayout, self).setGeometry(rect)
        self.doLayout(rect, False)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        size = QSize()

        for item in self.itemList:
            size = size.expandedTo(item.minimumSize())

        size += QSize(2 * self.margin, 2 * self.margin)
        return size

    def doLayout(self, rect, testOnly):
        x = rect.x()
        y = rect.y()
        lineHeight = 0

        for item in self.itemList:
            wid = item.widget()

            spaceX = self.horizontalSpacing()
            if spaceX == -1:
                spaceX = wid.style().layoutSpacing(
                    QSizePolicy.PushButton, QSizePolicy.PushButton, Qt.Horizontal)

            spaceY = self.verticalSpacing()
            if spaceY == -1:
                spaceY = wid.style().layoutSpacing(
                    QSizePolicy.PushButton, QSizePolicy.PushButton, Qt.Vertical)

            nextX = x + item.sizeHint().width() + spaceX
            if nextX - spaceX > rect.right() and lineHeight > 0:
                x = rect.x()
                y = y + lineHeight + spaceY
                nextX = x + item.sizeHint().width() + spaceX
                lineHeight = 0

            if not testOnly:
                item.setGeometry(QRect(QPoint(x, y), item.sizeHint()))

            x = nextX
            lineHeight = max(lineHeight, item.sizeHint().height())

        return y + lineHeight - rect.y()


class ImagePanelWidget(BaseWidget):
    widget_class_ = Ui_image_panel_widget
    page = 0
    total_per_page = 50
    page_step = 512
    last_page = False

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ui.scrollArea.verticalScrollBar().valueChanged.connect(self.handle_scroll)
        flowLayout = QFlowLayout()
        self.ui.scrollAreaWidgetContents.setLayout(flowLayout)
        if self.settings_manager.path_settings.image_path != "":
            base = ""
            path_parts = self.settings_manager.path_settings.image_path.split(os.sep)
            base = path_parts.pop()
            self.show_files()
        
        # watch the image directory for new files or delete files. if anything changes in the directory call show_files
        self.watcher = QFileSystemWatcher()
        # recursively watch the image path
        for root, dirs, files in os.walk(self.settings_manager.path_settings.image_path):
            self.watcher.addPath(root)
        
        self.watcher.directoryChanged.connect(self.handle_directory_changed)
        self.watcher.fileChanged.connect(self.handle_files_changed)
    
    def handle_directory_changed(self, event):
        self.show_files()
    
    def handle_files_changed(self, event):
        self.show_files()

    def clear_files(self):
        self.page = 0
        # remove all images from the container
        while self.ui.scrollAreaWidgetContents.layout().count() > 0:
            item = self.ui.scrollAreaWidgetContents.layout().takeAt(0)
            widget = item.widget()
            widget.deleteLater()

    def show_files(self, clear_images=True, reset_scroll_bar=True, show_folders=True):
        if clear_images:
            self.clear_files()

        if reset_scroll_bar:
            self.ui.scrollArea.verticalScrollBar().setValue(0)

        start = self.page * self.total_per_page
        end = start + self.total_per_page
        

        # recursively crawl self.settings_manager.path_settings.image_path and build a directory of the files sorted by the first folder name within self.settings_manager.path_settings.image_path
        # for example, self.settings_manager.path_settings.image_path will have several folders, those should be the key in a dictionary, and the value should be a list of files which is sorted by the most recent first
        files_in_image_path = os.listdir(self.settings_manager.path_settings.image_path)
        sorted_files = {}
        # recursively crawl the image path and build a dictionary of the files
        for file in files_in_image_path:
            if os.path.isdir(os.path.join(self.settings_manager.path_settings.image_path, file)):
                sorted_files[file] = []
                for root, dirs, files_in_dir in os.walk(os.path.join(self.settings_manager.path_settings.image_path, file)):
                    sorted_files[file].extend([os.path.join(root, f) for f in files_in_dir])
        
        section = "txt2img"
        files = sorted_files[section]
        # sort the files by the most recent first
        files.sort(key=os.path.getmtime, reverse=True)
        self.last_page = end >= len(files)
        for file in files[start:end]:
            if file.endswith(".png"):
                image_widget = ImageWidget(self)
                image_widget.set_image(os.path.join(self.settings_manager.path_settings.image_path, file))
                self.ui.scrollAreaWidgetContents.layout().addWidget(image_widget)
    
    def handle_folder_clicked(self, path):
        self.show_files()
    
    def handle_scroll(self, value):
        if self.last_page:
            return
        if value >= self.ui.scrollArea.verticalScrollBar().maximum() - self.page_step + 1:
            self.page += 1
            self.show_files(clear_images=False, reset_scroll_bar=False, show_folders=False)
