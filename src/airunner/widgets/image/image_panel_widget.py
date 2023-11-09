import os

from airunner.widgets.base_widget import BaseWidget
from airunner.widgets.image.folder_widget import FolderWidget
from airunner.widgets.image.image_widget import ImageWidget
from airunner.widgets.image.templates.image_panel_widget_ui import Ui_image_panel_widget


class ImagePanelWidget(BaseWidget):
    widget_class_ = Ui_image_panel_widget
    
    @property
    def image_path(self):
        return self.ui.breadcrumbs.absolute_path

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
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
    
    def handle_breadcrumb_clicked(self):
        self.show_files()

    def clear_files(self):
        # remove all images from the container
        while self.ui.scrollAreaWidgetContents.layout().count() > 0:
            item = self.ui.scrollAreaWidgetContents.layout().takeAt(0)
            widget = item.widget()
            widget.deleteLater()

    def show_files(self):
        self.clear_files()

        # first list all folders
        for file in os.listdir(self.image_path):
            if os.path.isdir(os.path.join(self.image_path, file)):
                folder_widget = FolderWidget()
                folder_widget.callback = self.handle_folder_clicked
                folder_widget.set_path(file)
                self.ui.scrollAreaWidgetContents.layout().addWidget(folder_widget)

        # list the first 10 files in the folder
        for file in os.listdir(self.image_path)[0:10]:
            if file.endswith(".png"):
                image_widget = ImageWidget(self)
                image_widget.set_image(os.path.join(self.image_path, file))
                self.ui.scrollAreaWidgetContents.layout().addWidget(image_widget)
    
    def handle_folder_clicked(self, path):
        self.ui.breadcrumbs.navigate(path)
        self.show_files()
