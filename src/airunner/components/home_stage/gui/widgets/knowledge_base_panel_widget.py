from PySide6.QtCore import Slot
from airunner.components.home_stage.gui.widgets.templates.knowledge_base_panel_ui import (
    Ui_knowledge_base_panel,
)
from airunner.components.application.gui.widgets.base_widget import BaseWidget
from airunner.enums import SignalCode


class KnowledgeBasePanelWidget(BaseWidget):
    """Widget for displaying document statistics and indexing controls."""

    widget_class_ = Ui_knowledge_base_panel

    def __init__(self, *args, **kwargs):
        self.signal_handlers = {
            SignalCode.RAG_INDEXING_PROGRESS: self.on_indexing_progress,
            SignalCode.RAG_INDEXING_COMPLETE: self.on_indexing_complete,
            SignalCode.DOCUMENT_COLLECTION_CHANGED: self.on_document_collection_changed,
            SignalCode.DOCUMENT_INDEXED: self.on_document_indexed,
        }
        super().__init__(*args, **kwargs)
        self.ui.index_button.clicked.connect(self.on_index_button_clicked)
        self.ui.cancel_button.clicked.connect(self.on_cancel_button_clicked)
        self.ui.cancel_button.setVisible(False)
        self.update_document_stats()
        self.clear_status_message_text()
        self.clear_progress_text()

    def update_document_stats(self):
        """Update document statistics from database."""
        try:
            from airunner.components.documents.data.models.document import (
                Document,
            )

            all_documents = Document.objects.all()
            total_documents = len(all_documents)
            indexed_documents = len([d for d in all_documents if d.indexed])
            unindexed_documents = total_documents - indexed_documents

            self.ui.total_docs_value.setText(str(total_documents))
            self.ui.indexed_docs_value.setText(str(indexed_documents))
            self.ui.unindexed_docs_value.setText(str(unindexed_documents))
        except Exception as e:
            self.logger.error(f"Error updating document stats: {e}")

    @Slot()
    def on_index_button_clicked(self):
        """Handle index button click."""
        self.ui.index_button.setVisible(False)
        self.ui.cancel_button.setVisible(True)
        self.ui.progress_bar.setValue(0)
        self.set_status_message_text("Indexing in progress...")
        self.emit_signal(SignalCode.RAG_INDEX_ALL_DOCUMENTS)

    @Slot()
    def on_cancel_button_clicked(self):
        """Handle cancel button click."""
        self.ui.cancel_button.setVisible(False)
        self.ui.index_button.setVisible(True)
        self.set_status_message_text("Indexing cancelled")
        self.emit_signal(SignalCode.RAG_INDEX_CANCEL)

    @Slot(dict)
    def on_indexing_progress(self, data: dict):
        """Handle indexing progress updates."""
        progress = data.get("progress", 0)
        total = data.get("total", 0)
        current = data.get("current", 0)

        if total > 0:
            percentage = int((current / total) * 100)
            self.ui.progress_bar.setValue(percentage)
            self.set_progress_text(f"Indexing: {current}/{total} documents")

    @Slot(dict)
    def on_document_indexed(self, data: dict):
        """Handle when a single document is indexed."""
        self.update_document_stats()

    @Slot(dict)
    def on_document_collection_changed(self, data: dict):
        """Handle when documents are added/removed from the collection."""
        self.update_document_stats()

    @Slot(dict)
    def on_indexing_complete(self, data: dict):
        """Handle indexing completion."""
        self.ui.cancel_button.setVisible(False)
        self.ui.index_button.setVisible(True)
        self.ui.progress_bar.setValue(100)
        self.set_status_message_text("Indexing complete")
        self.set_progress_text("")
        self.update_document_stats()

    def set_status_message_text(self, message: str):
        """Set the status message text."""
        if message != "":
            self.ui.status_message.show()
        else:
            self.ui.status_message.hide()
        self.ui.status_message.setText(message)

    def clear_status_message_text(self):
        """Clear the status message text."""
        self.set_status_message_text("")

    def set_progress_text(self, message: str):
        """Set the progress text."""
        if message != "":
            self.ui.progress_text.show()
        else:
            self.ui.progress_text.hide()
        self.ui.progress_text.setText(message)

    def clear_progress_text(self):
        """Clear the progress text."""
        self.set_progress_text("")
