from PySide6.QtCore import Slot

from airunner.widgets.base_widget import BaseWidget
from airunner.widgets.model_manager.templates.model_ui import Ui_model_widget


class ModelWidget(BaseWidget):
    widget_class_ = Ui_model_widget

    def __init__(self, *args, **kwargs):
        self.icons = [
            ("eye-look-icon", "toolButton"),
            ("recycle-bin-line-icon", "delete_button"),
        ]
        self.path = kwargs.pop("path")
        self.branch = kwargs.pop("branch")
        self.version = kwargs.pop("version")
        self.category = kwargs.pop("category")
        self.pipeline_action = kwargs.pop("pipeline_action")
        self.pipeline_class = kwargs.pop("pipeline_class")
        self.prompts = kwargs.pop("prompts", [])
        super().__init__(*args, **kwargs)
        self.hide_details()

        # details is a QTableWidget
        # we want to set the text of the second column, first row:
        # first, we will get the current item in the table
        self.ui.name.setText(self.path)
        self.ui.details.item(0, 1).setText(self.path)
        self.ui.details.item(1, 1).setText(self.branch)
        self.ui.details.item(2, 1).setText(self.version)
        self.ui.details.item(3, 1).setText(self.category)
        self.ui.details.item(4, 1).setText(self.pipeline_action)
        self.ui.details.item(5, 1).setText(self.pipeline_class)
        self.ui.details.item(6, 1).setText(",".join(self.prompts))

    @Slot(int, int)
    def action_cell_changed(self, row: int, column: int):
        # TODO: Implement this method
        pass

    def hide_details(self):
        # self.ui.details is a QGridLayout
        self.ui.details.hide()

    def show_details(self):
        self.ui.details.show()

    def action_toggled_button_details(self, val):
        self.show_details() if val else self.hide_details()

    def action_clicked_button_settings(self):
        print("edit button clicked")

    def action_clicked_button_delete(self):
        print("delete button clicked")
