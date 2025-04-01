
from airunner.gui.widgets.base_widget import BaseWidget
from airunner.gui.widgets.image.templates.folder_widget_ui import Ui_folder_widget


class FolderWidget(BaseWidget):
    widget_class_ = Ui_folder_widget
    path = None
    callback = None

    def set_path(self, path):
        self.path = path
        self.ui.label.setText(path)

    def folder_clicked(self):
        self.callback(self.path)
