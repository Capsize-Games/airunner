import os
from PySide6.QtCore import Slot
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QMessageBox

from airunner.components.documents.data.models.document import Document
from airunner.components.application.gui.widgets.base_widget import BaseWidget
from airunner.components.documents.gui.widgets.templates.document_ui import (
    Ui_document_widget,
)


class DocumentWidget(BaseWidget):
    widget_class_ = Ui_document_widget
    delete_requested = Signal(
        object
    )  # Emitted with the document to be deleted

    def __init__(
        self,
        document,
        on_active_changed=None,
        parent=None,
        title_truncate_length=50,
    ):
        # Force Qt.Widget flag and never Qt.Window
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.Widget)
        self.document = document
        self.on_active_changed = on_active_changed
        self.title_truncate_length = title_truncate_length
        self.setMinimumHeight(60)  # Ensure widget is visible
        self.setMinimumWidth(200)
        documents = Document.objects.filter_by(path=document.path)
        if not documents or len(documents) == 0:
            Document.objects.create(path=document.path, active=False)
        else:
            doc = documents[0]
            self.ui.checkBox.setChecked(doc.active)
        self.ui.checkBox.setText(self.document_title())
        self.ui.checkBox.setToolTip(os.path.basename(self.document.path))

    @Slot(bool)
    def on_checkBox_toggled(self, val: bool):
        documents = Document.objects.filter_by(path=self.document.path)
        if len(documents) > 0:
            document = documents[0]
            Document.objects.update(pk=document.id, active=val)

    @Slot()
    def on_delete_button_clicked(self):
        self.handle_delete()

    def document_title(self):
        # Use filename as title, truncated to self.title_truncate_length chars
        filename = os.path.basename(self.document.path)
        max_length = self.title_truncate_length
        if len(filename) > max_length:
            return filename[: max_length - 3] + "..."
        return filename

    def document_summary(self):
        # Try to read first 2 lines as summary
        try:
            with open(self.document.path, "r", encoding="utf-8") as f:
                lines = [next(f).strip() for _ in range(2)]
            return " ".join(lines)
        except Exception:
            return "(No preview available)"

    def handle_delete(self):
        reply = QMessageBox.question(
            self,
            "Delete Document",
            f"Are you sure you want to delete '{os.path.basename(self.document.path)}'? This cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            # Remove file from disk if it exists
            if os.path.exists(self.document.path):
                try:
                    os.remove(self.document.path)
                except Exception as e:
                    QMessageBox.warning(
                        self, "Error", f"Failed to delete file: {e}"
                    )
                    return
            # Remove from database using filter_by(path=...)
            docs = Document.objects.filter_by(path=self.document.path)
            for doc in docs:
                Document.objects.delete(doc.id)
        # No need to emit delete_requested; directory watcher will update the UI

    def sizeHint(self):
        return self.minimumSizeHint()
