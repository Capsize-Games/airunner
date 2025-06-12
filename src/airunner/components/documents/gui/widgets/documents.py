from typing import Dict
from airunner.components.documents.data.models.document import Document
from airunner.components.documents.gui.widgets.templates.documents_ui import (
    Ui_documents,
)

from airunner.gui.widgets.base_widget import BaseWidget
from PySide6.QtCore import Signal, Slot
from PySide6.QtGui import QIcon
from airunner.components.file_explorer.gui.widgets.file_explorer_widget import (
    FileExplorerWidget,
)
from airunner.enums import SignalCode
import os

from airunner.components.browser.gui.widgets.mixins.session_persistence_mixin import (
    SessionPersistenceMixin,
)
from airunner.components.browser.gui.widgets.mixins.privacy_mixin import (
    PrivacyMixin,
)
from airunner.components.browser.gui.widgets.mixins.panel_mixin import (
    PanelMixin,
)
from airunner.components.browser.gui.widgets.mixins.navigation_mixin import (
    NavigationMixin,
)
from airunner.components.browser.gui.widgets.mixins.summarization_mixin import (
    SummarizationMixin,
)
from airunner.components.browser.gui.widgets.mixins.cache_mixin import (
    CacheMixin,
)
from airunner.components.browser.gui.widgets.mixins.ui_setup_mixin import (
    UISetupMixin,
)
from airunner.utils.settings import get_qsettings


class DocumentsWidget(
    UISetupMixin,
    SessionPersistenceMixin,
    PrivacyMixin,
    PanelMixin,
    NavigationMixin,
    SummarizationMixin,
    CacheMixin,
    BaseWidget,
):
    """Widget that displays a file explorer for documents, reusing FileExplorerWidget."""

    titleChanged = Signal(str)
    urlChanged = Signal(str, str)  # url, title
    faviconChanged = Signal(QIcon)
    widget_class_ = Ui_documents

    def __init__(self, *args, private: bool = False, **kwargs):
        self._favicon = None
        self._private = private
        self.file_extensions = [
            "md",
            "txt",
            "docx",
            "doc",
            "odt",
            "pdf",
            "epub",
        ]
        self.signal_handlers = {
            SignalCode.DOCUMENT_INDEXED: self.on_document_indexed
        }
        super().__init__(*args, **kwargs)
        self.setup_file_explorer()

    def setup_file_explorer(self):
        widget = self.ui.treeView
        # Create and add the FileExplorerWidget
        self.file_explorer = FileExplorerWidget(
            path_to_display=self.documents_path, parent=self
        )
        self.file_explorer.setObjectName("fileExplorer")
        self.file_explorer.setMinimumSize(200, 200)
        self.ui.gridLayout.addWidget(self.file_explorer, 0, 0, 1, 1)
        self.file_explorer.ui.label.setText("Knowledge Base Documents")
        # Connect open signal
        self.file_explorer.connect_signal(
            SignalCode.FILE_EXPLORER_OPEN_FILE, self.on_file_open_requested
        )
        # Optionally filter extensions
        self._filter_file_explorer_extensions()

    def _filter_file_explorer_extensions(self):
        # Hide files that do not match allowed extensions
        model = self.file_explorer.model
        orig_filterAcceptsRow = (
            model.filterAcceptsRow
            if hasattr(model, "filterAcceptsRow")
            else None
        )
        allowed_exts = set(self.file_extensions)

        def filterAcceptsRow(row, parent):
            index = model.index(row, 0, parent)
            if not index.isValid():
                return False
            file_info = model.fileInfo(index)
            if file_info.isDir():
                return True
            ext = file_info.suffix().lower()
            return ext in allowed_exts

        model.filterAcceptsRow = filterAcceptsRow
        # If using QSortFilterProxyModel, set a filter here instead

    @property
    def documents_path(self) -> str:
        return os.path.join(
            os.path.expanduser(self.path_settings.base_path),
            "text/other/documents",
        )

    @documents_path.setter
    def documents_path(self, value: str):
        settings = get_qsettings()
        settings.setValue("documents_path", value)
        if hasattr(self, "file_explorer"):
            self.file_explorer.set_root_directory(value)

    @Slot(dict)
    def on_file_open_requested(self, data):
        file_path = data.get("file_path")
        if file_path:
            # Implement your document open logic here
            print(f"Open document: {file_path}")

    def on_document_indexed(self, data: Dict):
        print("ON DOCUMENT INDEXED", data)
        self._current_indexing += 1
        self._index_next_document()

    def showEvent(self, event):
        super().showEvent(event)
        self._sync_documents_with_directory()
        self._request_index_for_unindexed_documents()

    def _sync_documents_with_directory(self):
        print("*" * 100)
        print("syncing")
        # Ensure every file in the watched directory and subdirectories has a Document entry
        doc_dir = self.documents_path
        if not os.path.exists(doc_dir):
            self.logger.error(f"Document directory does not exist: {doc_dir}")
            return
        print("directory exists", doc_dir)
        for root, dirs, files in os.walk(doc_dir):
            for fname in files:
                fpath = os.path.join(root, fname)
                print("checking file", fpath)
                ext = os.path.splitext(fname)[1][1:].lower()
                if ext in self.file_extensions:
                    print("ext matches", ext)
                    exists = Document.objects.filter_by(path=fpath)
                    if not exists or len(exists) == 0:
                        print("Creating new Document entry for:", fpath)
                        Document.objects.create(path=fpath, active=True)
                    else:
                        print("Document already exists:", fpath)

    def _request_index_for_unindexed_documents(self):
        # Query all documents that are not indexed
        self._unindexed_docs = [
            doc.path
            for doc in Document.objects.filter(Document.indexed == False)
            if hasattr(doc, "path") and doc.path
        ]
        print("UNINDEX", self._unindexed_docs)
        self._total_to_index = len(self._unindexed_docs)
        self._current_indexing = 0
        if self._total_to_index == 0:
            self._clear_progress_bar()
            return
        self._index_next_document()

    def _index_next_document(self):
        if self._current_indexing < self._total_to_index:
            doc = self._unindexed_docs[self._current_indexing]
            percent = int(
                (self._current_indexing / self._total_to_index) * 100
            )
            filename = os.path.basename(getattr(doc, "path", str(doc)))
            truncated = (
                (filename[:32] + "...") if len(filename) > 35 else filename
            )
            self.ui.progressBar.setValue(percent)
            self.ui.progressBar.setFormat(
                f"Indexing {percent}% ({self._current_indexing+1} of {self._total_to_index} files) {truncated}"
            )
            self.ui.progressBar.setVisible(True)
            print("EMITTING SIGNAL CODE INDEX_DOCUMENT", doc)
            self.emit_signal(SignalCode.INDEX_DOCUMENT, {"path": doc})
        else:
            self._clear_progress_bar()

    def _clear_progress_bar(self):
        self.ui.progressBar.setValue(0)
        self.ui.progressBar.setFormat("")
        self.ui.progressBar.setVisible(False)
