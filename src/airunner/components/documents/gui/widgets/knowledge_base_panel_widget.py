import os
from typing import Dict, List

from PySide6.QtCore import QTimer, Qt, Slot
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QFileDialog, QMessageBox, QPushButton

from airunner_model.models.document import Document
from airunner.daemon_client.gui_daemon_client import GuiDaemonClient
from airunner.components.documents.document_import import (
    import_documents_to_library,
    is_rag_document_path,
    rag_document_suffixes,
)
from airunner.enums import SignalCode
from airunner.components.application.gui.widgets.base_widget import BaseWidget
from airunner.components.documents.gui.widgets.templates.knowledge_base_panel_ui import (
    Ui_knowledge_base_panel,
)


class KnowledgeBasePanelWidget(BaseWidget):
    """Small widget for showing document statistics and manual indexing controls.

    This class wraps the generated `Ui_knowledge_base_panel` UI so it can be
    reused in `DocumentsWidget` and other places. It emits the existing
    application signals for RAG indexing actions and listens for progress
    updates.
    """

    widget_class_ = Ui_knowledge_base_panel
    icons = [
        ("database", "index_button"),
        ("circle-x", "cancel_button"),
        ("import", "import_button"),
    ]

    def __init__(self, *args, **kwargs):
        # Track indexing progress locally
        self._total = 0
        self._current = 0
        self._document_name = ""
        self._daemon_client = GuiDaemonClient()
        self._index_status_timer = None
        self.signal_handlers = {
            SignalCode.DOCUMENT_COLLECTION_CHANGED: self.on_document_collection_changed,
            SignalCode.RAG_INDEXING_PROGRESS: self.on_indexing_progress,
            SignalCode.RAG_INDEXING_COMPLETE: self.on_indexing_complete,
        }
        super().__init__(*args, **kwargs)
        self._index_status_timer = QTimer(self)
        self._index_status_timer.setInterval(500)
        self._index_status_timer.timeout.connect(self._poll_index_status)
        self.setAcceptDrops(True)
        self._refresh_statistics()

    @property
    def documents_path(self) -> str:
        """Return the local AIRunner document library path."""
        configured = getattr(self.path_settings, "documents_path", None)
        if configured:
            return os.path.expanduser(configured)
        return os.path.join(
            os.path.expanduser(self.path_settings.base_path),
            "text/other/documents",
        )

    def _document_dialog_filter(self) -> str:
        """Return the file dialog filter for supported RAG documents."""
        document_patterns = " ".join(
            f"*{suffix}" for suffix in rag_document_suffixes()
        )
        return f"Documents ({document_patterns});;All Files (*)"

    @Slot()
    def on_import_button_clicked(self) -> None:
        """Import supported documents into the local AIRunner library."""
        file_paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Import document(s)",
            "",
            self._document_dialog_filter(),
        )
        self._import_documents(file_paths)

    def _import_documents(self, file_paths: List[str]) -> list[str]:
        """Copy selected files into the local knowledge-base folder."""
        if not file_paths:
            return []

        file_paths = [
            file_path
            for file_path in file_paths
            if is_rag_document_path(file_path)
        ]
        if not file_paths:
            return []

        imported_paths = import_documents_to_library(
            file_paths,
            self.documents_path,
        )
        if imported_paths:
            self.emit_signal(
                SignalCode.DOCUMENT_COLLECTION_CHANGED,
                {"paths": imported_paths},
            )
            self._refresh_statistics()
        return imported_paths

    def _refresh_statistics(self) -> None:
        """Refresh the displayed document counts from the document table."""
        total = 0
        indexed = 0
        for document in Document.objects.all():
            file_path = getattr(document, "path", None)
            if not file_path or not os.path.exists(file_path):
                continue
            total += 1
            if getattr(document, "indexed", False):
                indexed += 1

        self.ui.total_docs_value.setText(str(total))
        self.ui.indexed_docs_value.setText(str(indexed))
        self.ui.unindexed_docs_value.setText(str(max(total - indexed, 0)))

    @Slot()
    def on_index_button_clicked(self):
        """Request service-owned indexing for all known documents."""
        self.request_index_all_documents()

    @Slot()
    def on_cancel_button_clicked(self):
        """Request cancellation for one in-progress indexing flow."""
        self.logger.info(
            "KnowledgeBasePanel::Cancel clicked - requesting daemon cancellation"
        )
        try:
            self._daemon_client.cancel_rag_document_index()
        except Exception as exc:  # noqa: BLE001
            self.logger.error("Failed to cancel indexing: %s", exc)
            QMessageBox.critical(
                self,
                "Knowledge Base Indexing",
                f"Failed to cancel indexing:\n{exc}",
            )
        finally:
            self.ui.cancel_button.setEnabled(False)

    def request_index_all_documents(self) -> bool:
        """Request daemon-backed indexing for all documents."""
        return self._request_index_documents(file_paths=None)

    def request_index_selected_documents(
        self,
        file_paths: list[str],
    ) -> bool:
        """Request daemon-backed indexing for one explicit document list."""
        normalized = [path for path in file_paths if path]
        if not normalized:
            return False
        return self._request_index_documents(file_paths=normalized)

    def _request_index_documents(
        self,
        *,
        file_paths: list[str] | None,
    ) -> bool:
        """Send one indexing request to the daemon API."""
        scope = "all" if file_paths is None else f"{len(file_paths)} selected"
        self.logger.info(
            "KnowledgeBasePanel::request_index_documents - requesting %s documents via daemon API",
            scope,
        )
        self.ui.progress_bar.setRange(0, 0)
        self.ui.cancel_button.setEnabled(True)
        try:
            self._daemon_client.start_rag_document_index(
                file_paths=file_paths,
            )
            self._start_index_status_polling()
            return True
        except Exception as exc:  # noqa: BLE001
            self.logger.error("Failed to start indexing: %s", exc)
            self.ui.progress_bar.setRange(0, 100)
            self.ui.progress_bar.setValue(0)
            self.ui.cancel_button.setEnabled(False)
            QMessageBox.critical(
                self,
                "Knowledge Base Indexing",
                f"Failed to start indexing:\n{exc}",
            )
            return False

    def _start_index_status_polling(self) -> None:
        """Start polling daemon indexing status for cross-process updates."""
        if self._index_status_timer is None:
            return
        if not self._index_status_timer.isActive():
            self._index_status_timer.start()
        self._poll_index_status()

    def _stop_index_status_polling(self) -> None:
        """Stop polling daemon indexing status."""
        if self._index_status_timer is None:
            return
        self._index_status_timer.stop()

    def _poll_index_status(self) -> None:
        """Mirror daemon indexing status back into the local signal graph."""
        try:
            status = self._daemon_client.rag_document_index_status()
        except Exception as exc:  # noqa: BLE001
            self.logger.debug("Failed to poll indexing status: %s", exc)
            return

        payload = dict(status)
        payload["documentName"] = str(
            payload.get("document_name") or ""
        ).strip()

        if payload.get("active"):
            self.emit_signal(SignalCode.RAG_INDEXING_PROGRESS, payload)
            return

        if payload.get("success") is None:
            return

        self.emit_signal(SignalCode.RAG_INDEXING_COMPLETE, payload)
        self.emit_signal(SignalCode.DOCUMENT_COLLECTION_CHANGED, {})

    def on_indexing_progress(self, data: Dict):
        try:
            progress = int(data.get("progress", 0))
            current = int(data.get("current", 0))
            total = int(data.get("total", 0))
            document_name = data.get("documentName") or data.get(
                "document_name",
                "",
            )
            self._current = current
            self._total = total
            self._document_name = document_name
            if total <= 0:
                self.ui.progress_bar.setRange(0, 0)
            else:
                if self.ui.progress_bar.maximum() == 0:
                    self.ui.progress_bar.setRange(0, 100)
                self.ui.progress_bar.setValue(progress)
            self.ui.cancel_button.setEnabled(True)
        except Exception:
            pass

    def on_indexing_complete(self, data: Dict):
        self._stop_index_status_polling()
        try:
            self.ui.progress_bar.setRange(0, 100)
            if data.get("success", True):
                self.ui.progress_bar.setValue(100)
            else:
                self.ui.progress_bar.setValue(0)
        except Exception:
            pass
        self.ui.cancel_button.setEnabled(False)
        self._refresh_statistics()

    def on_document_collection_changed(self, _data: Dict):
        """Refresh counts after imported or deleted document changes."""
        self._refresh_statistics()

    def showEvent(self, event):
        super().showEvent(event)
        self._refresh_statistics()

    def dragEnterEvent(self, event) -> None:
        """Accept supported document drags for knowledge-base import."""
        if self._extract_importable_paths(event.mimeData()):
            event.acceptProposedAction()
            return
        super().dragEnterEvent(event)

    def dropEvent(self, event) -> None:
        """Import supported documents dropped onto the panel widget."""
        file_paths = self._extract_importable_paths(event.mimeData())
        if not file_paths:
            super().dropEvent(event)
            return
        self._import_documents(file_paths)
        event.acceptProposedAction()

    def _extract_importable_paths(self, mime_data) -> list[str]:
        """Return supported local document paths from one mime payload."""
        if not mime_data.hasUrls():
            return []

        file_paths: list[str] = []
        for url in mime_data.urls():
            path = url.toLocalFile()
            if not path or not os.path.exists(path):
                continue
            if not is_rag_document_path(path):
                continue
            file_paths.append(path)
        return file_paths
