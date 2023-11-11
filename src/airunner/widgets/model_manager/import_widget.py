from airunner.widgets.base_widget import BaseWidget
from airunner.widgets.model_manager.templates.import_ui import Ui_import_model_widget


class ImportWidget(BaseWidget):
    widget_class_ = Ui_import_model_widget
    model_widgets = []

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.show_import_form()

    def action_clicked_button_import(self):
        self.show_model_select_form()

    def action_clicked_button_download(self):
        self.show_download_form()

    def action_clicked_button_cancel(self):
        self.show_import_form()

    def show_import_form(self):
        self.ui.import_form.show()
        self.ui.model_select_form.hide()
        self.ui.download_form.hide()

    def show_model_select_form(self):
        self.ui.import_form.hide()
        self.ui.model_select_form.show()
        self.ui.download_form.hide()

    def show_download_form(self):
        self.ui.import_form.hide()
        self.ui.model_select_form.hide()
        self.ui.download_form.show()
