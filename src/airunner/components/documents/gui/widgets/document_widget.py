import os
from PySide6.QtCore import Slot, Qt, Signal
from PySide6.QtWidgets import QMessageBox

from airunner.components.application.gui.widgets.base_widget import BaseWidget
from airunner.components.documents.data.document_records import (
    delete_documents_by_path,
    ensure_document_record,
    find_document_by_path,
    update_document,
)
from airunner.components.documents.gui.widgets.templates.document_ui import (
    Ui_document_widget,
)


class DocumentWidget(BaseWidget):
    ui: Ui_document_widget  # type: ignore[assignment]
    """Widget representing a single document in the unified RAG collection."""

    widget_class_ = Ui_document_widget
    delete_requested = Signal(object)

    def __init__(
        self,
        document,
        on_active_changed=None,
        parent=None,
        title_truncate_length=50,
    ):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.Widget)
        self.document = document
        self.on_active_changed = on_active_changed
        self.title_truncate_length = title_truncate_length
        self.setMinimumHeight(60)
        self.setMinimumWidth(200)

        doc = ensure_document_record(
            document.path,
            active=False,
            indexed=False,
        )
        if doc is not None:
            self.ui.checkBox.setChecked(doc.active)

            # Show indexed status in tooltip
            indexed_status = "✓ Indexed" if doc.indexed else "Not Indexed"
            self.ui.checkBox.setToolTip(
                f"{os.path.basename(self.document.path)}\n{indexed_status}"
            )

        self.ui.checkBox.setText(self.document_title())

    @Slot(bool)
    def on_checkBox_toggled(self, val: bool):
        """Toggle active status (for display/organization purposes)."""
        document = find_document_by_path(self.document.path)
        if document is not None:
            update_document(document.id, {"active": val})

    @Slot()
    def on_delete_button_clicked(self):
        self.handle_delete()

    def document_title(self) -> str:
        """Get truncated document filename."""
        filename = os.path.basename(self.document.path)
        max_length = self.title_truncate_length
        if len(filename) > max_length:
            return f"{filename[:max_length - 3]}..."
        return filename

    def handle_delete(self):
        """Delete document from disk and database."""
        reply = QMessageBox.question(
            self,
            "Delete Document",
            f"Are you sure you want to delete '{os.path.basename(self.document.path)}'? "
            "This will remove it from the RAG collection and cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            if os.path.exists(self.document.path):
                try:
                    os.remove(self.document.path)
                except Exception as e:
                    QMessageBox.warning(
                        self, "Error", f"Failed to delete file: {e}"
                    )
                    return

            delete_documents_by_path(self.document.path)

    def sizeHint(self):
        return self.minimumSizeHint()
