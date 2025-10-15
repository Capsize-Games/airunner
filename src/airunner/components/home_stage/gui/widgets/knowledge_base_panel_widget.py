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
            SignalCode.RAG_INDEX_SELECTED_DOCUMENTS: self.on_index_selected_documents,
        }
        super().__init__(*args, **kwargs)
        self.ui.index_button.clicked.connect(self.on_index_button_clicked)
        self.ui.cancel_button.clicked.connect(self.on_cancel_button_clicked)
        self.ui.cancel_button.setVisible(False)
        self.update_document_stats()
        self.clear_status_message_text()
        # We only use a single status label now; hide the separate progress text
        try:
            self.ui.progress_text.hide()
        except Exception:
            pass

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
        # Switch the progress bar to indeterminate (busy) mode
        try:
            self.ui.progress_bar.setRange(0, 0)
        except Exception:
            # Fallback: set to 0 if setRange not available
            try:
                self.ui.progress_bar.setValue(0)
            except Exception:
                pass
        self.set_status_message_text("Indexing in progress...")
        self.emit_signal(SignalCode.RAG_INDEX_ALL_DOCUMENTS)

    @Slot(dict)
    def on_index_selected_documents(self, data: dict):
        """Handle selective document indexing request."""
        file_paths = data.get("file_paths", [])
        if not file_paths:
            return

        self.logger.info(
            f"Starting selective indexing for {len(file_paths)} documents"
        )
        self.ui.index_button.setVisible(False)
        self.ui.cancel_button.setVisible(True)
        # Show indeterminate/busy progress while indexing selected docs
        try:
            self.ui.progress_bar.setRange(0, 0)
        except Exception:
            try:
                self.ui.progress_bar.setValue(0)
            except Exception:
                pass
        self.set_status_message_text(
            f"Indexing {len(file_paths)} documents..."
        )

        # Forward to worker with file paths
        self.emit_signal(
            SignalCode.RAG_INDEX_SELECTED_DOCUMENTS, {"file_paths": file_paths}
        )

    @Slot()
    def on_cancel_button_clicked(self):
        """Handle cancel button click."""
        self.ui.cancel_button.setVisible(False)
        self.ui.index_button.setVisible(True)
        self.set_status_message_text("Indexing cancelled")
        # Restore determinate progress bar state
        try:
            self.ui.progress_bar.setRange(0, 100)
            self.ui.progress_bar.setValue(0)
        except Exception:
            pass
        self.emit_signal(SignalCode.RAG_INDEX_CANCEL)

    @Slot(dict)
    def on_indexing_progress(self, data: dict):
        """Handle indexing progress updates."""
        progress = data.get("progress", 0)
        total = data.get("total", 0)
        current = data.get("current", 0)
        # Keep the progress bar in indeterminate mode; update the single
        # status label with a concise message showing current/total.
        if total > 0:
            self.set_status_message_text(
                f"Indexing: {current}/{total} documents"
            )
        elif progress:
            # Fallback to a simple status when total unknown
            self.set_status_message_text(f"Indexing... ({progress})")

    @Slot(dict)
    def on_document_indexed(self, data: dict):
        """Handle when a single document is indexed."""
        self.update_document_stats()

    @Slot(dict)
    def on_document_collection_changed(self, data: dict):
        print("ON DOCUMENT COLLECTION CHANGED: knowledge_base_panel.py")
        """Handle when documents are added/removed from the collection."""
        self.update_document_stats()

    @Slot(dict)
    def on_indexing_complete(self, data: dict):
        """Handle indexing completion."""
        self.ui.cancel_button.setVisible(False)
        self.ui.index_button.setVisible(True)
        # Restore determinate progress bar and mark complete
        try:
            self.ui.progress_bar.setRange(0, 100)
            self.ui.progress_bar.setValue(100)
        except Exception:
            try:
                self.ui.progress_bar.setValue(100)
            except Exception:
                pass
        self.set_status_message_text("Indexing complete")
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
        # Consolidate progress text into the single status_message label
        # Keep the progress_text widget present for compatibility but do not use it.
        self.set_status_message_text(message)

    def clear_progress_text(self):
        """Clear the progress text."""
        self.set_status_message_text("")
