from airunner.widgets.base_widget import BaseWidget
from airunner.widgets.breadcrumbs.templates.breadcrumb_ui import Ui_breadcrumb_widget


class BreadcrumbWidget(BaseWidget):
    widget_class_ = Ui_breadcrumb_widget
    path = ""
    folder = ""
    is_final = True
    is_home = False
    
    def toggle_elements(self):
        self.ui.button.setVisible(not self.is_home)
        self.ui.home_button.setVisible(self.is_home)
        self.ui.slash.setVisible(not self.is_final)
        button_enabled = not self.is_final
        self.ui.button.setEnabled(button_enabled)
        self.ui.home_button.setEnabled(button_enabled)

    def __init__(self, *args, **kwargs):
        self._parent = kwargs.pop("parent")
        super().__init__(*args, **kwargs)

    def set_path(self, path, is_final, is_home=False):
        self.path = path
        self.is_final = is_final
        self.is_home = is_home
        path = path.title()
        self.ui.button.setText(path)
        self.ui.home_button.setText(path)
        self.toggle_elements()
    
    def breadcrumb_clicked(self):
        self._parent.handle_breadcrumb_clicked(self.folder)
