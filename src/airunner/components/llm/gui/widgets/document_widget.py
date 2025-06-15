from PySide6.QtCore import Slot

from airunner.components.application.gui.widgets.base_widget import BaseWidget
from airunner.components.llm.gui.widgets.templates.document_widget_ui import (
    Ui_document_widget,
)


class DocumentWidget(BaseWidget):
    widget_class_ = Ui_document_widget

    def __init__(self, target_file, delete_function, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.text = target_file.file_path
        self.delete_function = delete_function
        self.target_file = target_file
        self.ui.label.setText(self.text)

    @Slot()
    def on_delete(self):
        self.delete_function(self.target_file)
        self.deleteLater()
