import os

from PyQt6.QtWidgets import QWidget, QHBoxLayout
from PyQt6 import QtWidgets
from PyQt6.QtCore import QFileSystemWatcher


from airunner.widgets.base_widget import BaseWidget
from airunner.widgets.image.folder_widget import FolderWidget
from airunner.widgets.image.image_widget import ImageWidget
from airunner.widgets.image.templates.image_panel_widget_ui import Ui_image_panel_widget


class ImagePanelWidget(BaseWidget):
    widget_class_ = Ui_image_panel_widget
    page = 0
    total_per_page = 10
    page_step = 512
    last_page = False
    
    @property
    def image_path(self):
        return self.ui.breadcrumbs.absolute_path

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ui.scrollArea.verticalScrollBar().valueChanged.connect(self.handle_scroll)
        self.ui.breadcrumbs.callback = self.handle_breadcrumb_clicked
        if self.settings_manager.path_settings.image_path != "":
            base = ""
            path_parts = self.settings_manager.path_settings.image_path.split(os.sep)
            base = path_parts.pop()
            self.ui.breadcrumbs.callback = self.handle_breadcrumb_clicked
            self.ui.breadcrumbs.path_base = base
            self.ui.breadcrumbs.root_path = os.sep.join(path_parts)
            self.ui.breadcrumbs.update_breadcrumbs(base)
            self.show_files()
        
        # watch the image directory for new files or delete files. if anything changes in the directory call show_files
        self.watcher = QFileSystemWatcher()
        self.watcher.addPath(self.image_path)
        self.watcher.directoryChanged.connect(self.handle_directory_changed)
        self.watcher.fileChanged.connect(self.handle_files_changed)
    
    def handle_breadcrumb_clicked(self):
        self.show_files()
    
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
        
        if show_folders:
            container = QWidget()
            container.setLayout(QHBoxLayout())
            container.setObjectName("folder_container")
            # set the width to stretch
            container.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Fixed)
            for file in os.listdir(self.image_path):
                if os.path.isdir(os.path.join(self.image_path, file)):
                    folder_widget = FolderWidget()
                    folder_widget.callback = self.handle_folder_clicked
                    folder_widget.set_path(file)
                    container.layout().addWidget(folder_widget)
            self.ui.scrollAreaWidgetContents.layout().addWidget(container)

        start = self.page * self.total_per_page
        end = start + self.total_per_page
        

        # recursively crawl self.image_path and build a directory of the files sorted by the first folder name within self.image_path
        # for example, self.image_path will have several folders, those should be the key in a dictionary, and the value should be a list of files which is sorted by the most recent first
        files_in_image_path = os.listdir(self.image_path)
        sorted_files = {}
        # recursively crawl the image path and build a dictionary of the files
        for file in files_in_image_path:
            if os.path.isdir(os.path.join(self.image_path, file)):
                sorted_files[file] = []
                for root, dirs, files_in_dir in os.walk(os.path.join(self.image_path, file)):
                    sorted_files[file].extend([os.path.join(root, f) for f in files_in_dir])
        
        section = "txt2img"
        files = sorted_files[section]
        # sort the files by the most recent first
        files.sort(key=os.path.getmtime, reverse=True)
        self.last_page = end >= len(files)
        for file in files[start:end]:
            if file.endswith(".png"):
                image_widget = ImageWidget(self)
                image_widget.set_image(os.path.join(self.image_path, file))
                self.ui.scrollAreaWidgetContents.layout().addWidget(image_widget)
    
    def handle_folder_clicked(self, path):
        self.ui.breadcrumbs.navigate(path)
        self.show_files()
    
    def handle_scroll(self, value):
        if self.last_page:
            return
        if value >= self.ui.scrollArea.verticalScrollBar().maximum() - self.page_step + 1:
            self.page += 1
            self.show_files(clear_images=False, reset_scroll_bar=False, show_folders=False)
