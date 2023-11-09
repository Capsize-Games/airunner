import os

from airunner.widgets.base_widget import BaseWidget
from airunner.widgets.breadcrumbs.templates.breadcrumb_container_widget_ui import Ui_breadcrumb_container_widget
from airunner.widgets.breadcrumbs.breadcrumb_widget import BreadcrumbWidget

class BreadcrumbContainerWidget(BaseWidget):
    widget_class_ = Ui_breadcrumb_container_widget
    current_path = ""
    path_base = ""
    root_path = ""

    @property
    def absolute_path(self):
        return os.path.join(self.root_path, self.current_path)

    def clear_breadcrumbs(self):
        # remove all breadcrumbs from the container
        while self.ui.breadcrumb_container.count() > 0:
            item = self.ui.breadcrumb_container.takeAt(0)
            widget = item.widget()
            widget.deleteLater()

    def navigate(self, path):
        self.update_breadcrumbs(path)

    def update_breadcrumbs(self, path):
        if path != "":
            self.current_path = os.path.join(self.current_path, path)

        self.clear_breadcrumbs()
        is_final = True
        path_parts = self.current_path.split(os.sep)
        is_final = True
        for index, path in enumerate(path_parts):
            is_home = index == 0
            is_final = index == len(path_parts) - 1
            self.add_breadcrumb(path, is_final, is_home)
        
    def handle_breadcrumb_clicked(self, folder):
        path_parts = self.current_path.split(os.sep)
        while len(path_parts) > 0:
            if path_parts[-1] == folder:
                break
            path_parts.pop()
        self.current_path = os.sep.join(path_parts)
        self.update_breadcrumbs("")
        self.callback()
    
    def add_breadcrumb(self, path, is_final=False, is_home=False):
        breadcrumb_widget = BreadcrumbWidget(parent=self)
        breadcrumb_widget.folder = path
        breadcrumb_widget.set_path(path, is_final, is_home)
        self.ui.breadcrumb_container.addWidget(breadcrumb_widget)