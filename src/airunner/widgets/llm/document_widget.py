from PySide6.QtCore import Slot

from airunner.widgets.base_widget import BaseWidget
from airunner.widgets.llm.templates.document_widget_ui import Ui_document_widget


class DocumentWidget(BaseWidget):
    widget_class_ = Ui_document_widget

    def __init__(self, text, delete_function, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.text = text
        self.delete_function = delete_function
        self.ui.label.setText(text)

    @Slot()
    def on_delete(self):
        self.delete_function(self.text)
        self.deleteLater()
