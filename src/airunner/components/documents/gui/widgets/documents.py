from typing import Dict
import os

from PySide6.QtCore import (
    Signal,
    Qt,
    QEvent,
)
from PySide6.QtGui import (
    QIcon,
    QStandardItemModel,
    QStandardItem,
    QAction,
)
from PySide6.QtWidgets import (
    QFileSystemModel,
    QAbstractItemView,
    QMenu,
    QMessageBox,
)

from airunner.enums import SignalCode
from airunner.utils.settings import get_qsettings
from airunner.components.application.gui.widgets.base_widget import BaseWidget
from airunner.components.documents.data.models.document import Document
from airunner.components.documents.gui.widgets.templates.documents_ui import (
    Ui_documents,
)
from airunner.components.documents.gui.widgets.kiwix_widget import KiwixWidget


class DocumentsWidget(BaseWidget):
    """Widget for document management and file exploration."""

    titleChanged = Signal(str)
    urlChanged = Signal(str, str)
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
            "zim",
        ]
        self.signal_handlers = {
            SignalCode.DOCUMENT_INDEXED: self.on_document_indexed,
            SignalCode.DOCUMENT_INDEX_FAILED: self.on_document_index_failed,
            SignalCode.DOCUMENT_COLLECTION_CHANGED: self.on_document_collection_changed,
        }
        super().__init__(*args, **kwargs)
        self.setup_file_explorer()
        self.kiwix_widget = KiwixWidget()
        self.setup_kiwix_widget()

    def setup_file_explorer(self):
        # Setup available documents tree (file system view)
        self.documents_model = QFileSystemModel(self)
        doc_dir = self.documents_path
        if not os.path.exists(doc_dir):
            os.makedirs(doc_dir, exist_ok=True)
        self.documents_model.setRootPath(doc_dir)
        self.ui.documentsTreeView.setModel(self.documents_model)
        self.ui.documentsTreeView.setRootIndex(
            self.documents_model.index(doc_dir)
        )
        self.ui.documentsTreeView.setColumnHidden(1, True)
        self.ui.documentsTreeView.setColumnHidden(2, True)
        self.ui.documentsTreeView.setColumnHidden(3, True)
        self.ui.documentsTreeView.setHeaderHidden(True)
        self.ui.documentsTreeView.setSelectionMode(
            QAbstractItemView.SelectionMode.ExtendedSelection
        )
        self.ui.documentsTreeView.setDragEnabled(True)
        self.ui.documentsTreeView.setDragDropMode(
            QAbstractItemView.DragDropMode.DragOnly
        )

        # Setup active documents tree (manual selection)
        self.active_documents_model = QStandardItemModel(self)
        self.ui.activeDocumentsTreeView.setModel(self.active_documents_model)
        self.ui.activeDocumentsTreeView.setHeaderHidden(True)
        self.ui.activeDocumentsTreeView.setAcceptDrops(True)
        self.ui.activeDocumentsTreeView.setDragEnabled(True)
        self.ui.activeDocumentsTreeView.setDragDropMode(
            QAbstractItemView.DragDropMode.DragDrop
        )
        self.ui.activeDocumentsTreeView.setSelectionMode(
            QAbstractItemView.SelectionMode.ExtendedSelection
        )

        # Setup unavailable documents tree (failed to index)
        self.unavailable_documents_model = QStandardItemModel(self)
        self.ui.unavailableDocumentsTreeView.setModel(
            self.unavailable_documents_model
        )
        self.ui.unavailableDocumentsTreeView.setHeaderHidden(True)
        self.ui.unavailableDocumentsTreeView.setSelectionMode(
            QAbstractItemView.SelectionMode.ExtendedSelection
        )

        # Connect drag-and-drop signals
        self.ui.documentsTreeView.clicked.connect(
            self.on_available_doc_clicked
        )
        self.ui.activeDocumentsTreeView.clicked.connect(
            self.on_active_doc_clicked
        )

        # Add context menus
        self.ui.documentsTreeView.setContextMenuPolicy(
            Qt.ContextMenuPolicy.CustomContextMenu
        )
        self.ui.documentsTreeView.customContextMenuRequested.connect(
            self.show_available_doc_context_menu
        )
        self.ui.activeDocumentsTreeView.setContextMenuPolicy(
            Qt.ContextMenuPolicy.CustomContextMenu
        )
        self.ui.activeDocumentsTreeView.customContextMenuRequested.connect(
            self.show_active_doc_context_menu
        )
        self.ui.unavailableDocumentsTreeView.setContextMenuPolicy(
            Qt.ContextMenuPolicy.CustomContextMenu
        )
        self.ui.unavailableDocumentsTreeView.customContextMenuRequested.connect(
            self.show_unavailable_doc_context_menu
        )

        # Enable custom drag and drop handling
        self.ui.documentsTreeView.setDefaultDropAction(
            Qt.DropAction.CopyAction
        )
        self.ui.activeDocumentsTreeView.viewport().installEventFilter(self)

        # Load active documents from database
        self.refresh_active_documents_list()

    def setup_kiwix_widget(self):
        """Initialize the Kiwix widget with UI components."""
        self.kiwix_widget.initialize(
            local_zims_list=self.ui.listLocalZims,
            search_results_list=self.ui.listRemoteZims,
            kiwix_search_bar=self.ui.kiwixSearchBar,
            kiwix_lang_combo=self.ui.kiwixLangCombo,
            kiwix_search_button=self.ui.kiwixSearchButton,
        )

    def on_file_open_requested(self, data):
        file_path = data.get("file_path")
        if file_path:
            # Implement your document open logic here
            print(f"Open document: {file_path}")

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

    def on_document_indexed(self, data: Dict):
        """Handle successful document indexing."""
        self._current_indexing += 1
        self._index_next_document()

        # Refresh the document lists to show updated indexing status
        self.refresh_active_documents_list()

        # Log success
        document_path = data.get("path", "")
        if document_path:
            fname = os.path.basename(document_path)
            self.logger.info(f"Document indexed successfully: {fname}")

    def on_document_index_failed(self, data: Dict):
        """Handle failed document indexing."""
        document_path = data.get("path", "")
        error = data.get("error", "Unknown error")

        if document_path:
            fname = os.path.basename(document_path)
            self.logger.error(f"Failed to index document {fname}: {error}")

            # Show error message to user
            QMessageBox.warning(
                self,
                "Document Indexing Failed",
                f"Failed to index document:\n\n{fname}\n\nError: {error}\n\n"
                f"This document may be corrupted, empty, or in an unsupported format.",
                QMessageBox.Ok,
            )

        # Refresh the document lists - document should stay in unavailable
        self.refresh_active_documents_list()

    def eventFilter(self, obj, event):
        """Handle drag-and-drop events for the active documents tree."""
        if obj == self.ui.activeDocumentsTreeView.viewport():
            if event.type() == QEvent.Type.DragEnter:
                event.acceptProposedAction()
                return True
            elif event.type() == QEvent.Type.Drop:
                self.handle_drop_on_active_list(event)
                return True
        return super().eventFilter(obj, event)

    def on_available_doc_clicked(self, index):
        """Handle double-click on available documents to add to active list."""
        pass  # Single click does nothing, use drag-and-drop

    def on_active_doc_clicked(self, index):
        """Handle click on active documents."""
        pass  # Can be extended for context menu, etc.

    def handle_drop_on_active_list(self, event):
        """Handle files dropped onto the active documents list."""
        mime_data = event.mimeData()

        # Handle file paths from file system view
        if mime_data.hasUrls():
            for url in mime_data.urls():
                file_path = url.toLocalFile()
                if os.path.isfile(file_path):
                    self.add_document_to_active(file_path)
                elif os.path.isdir(file_path):
                    # Handle dropped folder - add all documents within it
                    self.add_folder_documents_to_active(file_path)
            event.acceptProposedAction()

    def add_folder_documents_to_active(self, folder_path: str):
        """Add all documents from a folder to the active RAG collection."""
        for root, dirs, files in os.walk(folder_path):
            for fname in files:
                ext = os.path.splitext(fname)[1][1:].lower()
                if ext in self.file_extensions and ext != "zim":
                    file_path = os.path.join(root, fname)
                    self.add_document_to_active(file_path)

    def add_document_to_active(self, file_path: str):
        """Add a document to the active RAG collection."""
        # Check if already in active list
        for row in range(self.active_documents_model.rowCount()):
            item = self.active_documents_model.item(row, 0)
            if item and item.data() == file_path:
                self.logger.info(
                    f"Document already active: {os.path.basename(file_path)}"
                )
                return

        # Add to model
        filename = os.path.basename(file_path)
        item = QStandardItem(filename)
        item.setData(file_path)
        item.setEditable(False)
        self.active_documents_model.appendRow(item)

        # Update database
        docs = Document.objects.filter_by(path=file_path)
        if docs and len(docs) > 0:
            Document.objects.update(pk=docs[0].id, active=True)
        else:
            Document.objects.create(path=file_path, active=True, indexed=False)

        self.logger.info(f"Added to active documents: {filename}")

    def remove_document_from_active(self, file_path: str):
        """Remove a document from the active RAG collection."""
        # Safety check
        if not file_path:
            self.logger.warning("Attempted to remove document with None path")
            return

        # Remove from model
        for row in range(self.active_documents_model.rowCount()):
            item = self.active_documents_model.item(row, 0)
            if item and item.data() == file_path:
                self.active_documents_model.removeRow(row)
                break

        # Update database
        docs = Document.objects.filter_by(path=file_path)
        if docs and len(docs) > 0:
            Document.objects.update(pk=docs[0].id, active=False)

        filename = os.path.basename(file_path)
        self.logger.info(f"Removed from active documents: {filename}")

    def refresh_active_documents_list(self):
        """Load active and unavailable documents from database into the tree views."""
        self.active_documents_model.clear()
        self.unavailable_documents_model.clear()

        # Get all documents from database
        all_docs = Document.objects.all()

        for doc in all_docs:
            if not os.path.exists(doc.path):
                continue

            filename = os.path.basename(doc.path)
            item = QStandardItem(filename)
            item.setData(doc.path)
            item.setEditable(False)

            # Determine which list to add to
            if doc.active and doc.indexed:
                # Active and indexed - add to active list
                item.setToolTip(f"{filename}\n✓ Indexed and ready for RAG")
                self.active_documents_model.appendRow(item)
            elif doc.active and not doc.indexed:
                # Active but not indexed - try to index
                # If it repeatedly fails to index, it might be unavailable
                # For now, keep it in active list with warning
                item.setToolTip(f"{filename}\n⚠ Not yet indexed")
                self.active_documents_model.appendRow(item)
            elif not doc.active and not doc.indexed:
                # Not active and not indexed - likely unavailable
                item.setToolTip(f"{filename}\n✗ Failed to index")
                self.unavailable_documents_model.appendRow(item)

    def keyPressEvent(self, event):
        """Handle keyboard shortcuts (Delete key to remove from active list)."""
        if event.key() == Qt.Key.Key_Delete:
            # Check which tree view has focus
            if self.ui.activeDocumentsTreeView.hasFocus():
                selected = self.ui.activeDocumentsTreeView.selectedIndexes()
                for index in selected:
                    item = self.active_documents_model.itemFromIndex(index)
                    if item:
                        file_path = item.data()
                        self.remove_document_from_active(file_path)
                return

        super().keyPressEvent(event)

    def show_available_doc_context_menu(self, position):
        """Show context menu for available documents."""
        index = self.ui.documentsTreeView.indexAt(position)
        if not index.isValid():
            return

        # Get all selected indexes
        selected_indexes = self.ui.documentsTreeView.selectedIndexes()
        if not selected_indexes:
            return

        # Collect files and folders
        selected_files = []
        selected_folders = []
        for idx in selected_indexes:
            file_path = self.documents_model.filePath(idx)
            if os.path.isfile(file_path):
                selected_files.append(file_path)
            elif os.path.isdir(file_path):
                selected_folders.append(file_path)

        if not selected_files and not selected_folders:
            return

        menu = QMenu(self)

        # Show appropriate label based on selection
        total_items = len(selected_files) + len(selected_folders)
        if total_items == 1:
            if selected_files:
                add_action = QAction("Add to Active Documents (RAG)", self)
                delete_action = QAction("Delete", self)
            else:
                add_action = QAction(
                    "Add Folder to Active Documents (RAG)", self
                )
                delete_action = QAction("Delete Folder", self)
        else:
            add_action = QAction(
                f"Add {total_items} Items to Active (RAG)", self
            )
            delete_action = QAction(f"Delete {total_items} Items", self)

        # Add all selected files and folders
        def add_selected():
            for file_path in selected_files:
                self.add_document_to_active(file_path)
            for folder_path in selected_folders:
                self.add_folder_documents_to_active(folder_path)

        # Delete selected files and folders from database AND disk
        def delete_selected():
            for file_path in selected_files:
                # Delete from database
                docs = Document.objects.filter_by(path=file_path)
                if docs and len(docs) > 0:
                    Document.objects.delete(pk=docs[0].id)

                # Delete the actual file from disk
                try:
                    if os.path.exists(file_path):
                        os.remove(file_path)
                        fname = os.path.basename(file_path)
                        self.logger.info(
                            f"Deleted document from database and disk: {fname}"
                        )
                except Exception as e:
                    fname = os.path.basename(file_path)
                    self.logger.error(
                        f"Failed to delete file from disk {fname}: {e}"
                    )

            for folder_path in selected_folders:
                # Delete all documents in the folder from database and disk
                import shutil

                try:
                    if os.path.exists(folder_path):
                        # First delete from database
                        for root, dirs, files in os.walk(folder_path):
                            for fname in files:
                                file_path = os.path.join(root, fname)
                                docs = Document.objects.filter_by(
                                    path=file_path
                                )
                                if docs and len(docs) > 0:
                                    Document.objects.delete(pk=docs[0].id)

                        # Then delete the folder from disk
                        shutil.rmtree(folder_path)
                        self.logger.info(
                            f"Deleted folder from database and disk: {os.path.basename(folder_path)}"
                        )
                except Exception as e:
                    self.logger.error(
                        f"Failed to delete folder {folder_path}: {e}"
                    )

            self.refresh_active_documents_list()
            self.emit_signal(SignalCode.DOCUMENT_COLLECTION_CHANGED)

        add_action.triggered.connect(add_selected)
        delete_action.triggered.connect(delete_selected)
        menu.addAction(add_action)
        menu.addAction(delete_action)
        menu.exec(self.ui.documentsTreeView.viewport().mapToGlobal(position))

    def show_active_doc_context_menu(self, position):
        """Show context menu for active documents."""
        index = self.ui.activeDocumentsTreeView.indexAt(position)
        if not index.isValid():
            return

        # Get all selected indexes (not just the one right-clicked)
        selected_indexes = self.ui.activeDocumentsTreeView.selectedIndexes()
        if not selected_indexes:
            return

        menu = QMenu(self)

        # Show appropriate label based on selection count
        if len(selected_indexes) == 1:
            remove_action = QAction("Remove from Active Documents", self)
            delete_action = QAction("Delete", self)
        else:
            remove_action = QAction(
                f"Remove {len(selected_indexes)} Documents from Active", self
            )
            delete_action = QAction(
                f"Delete {len(selected_indexes)} Documents", self
            )

        # Remove all selected documents (deactivate - set active=False)
        def remove_selected():
            # Collect all file paths first (before removing any items)
            file_paths = []
            for idx in selected_indexes:
                item = self.active_documents_model.itemFromIndex(idx)
                if item:
                    file_path = item.data()
                    if file_path:  # Check file_path is not None
                        file_paths.append(file_path)

            # Now remove all collected paths
            for file_path in file_paths:
                self.remove_document_from_active(file_path)

        # Delete selected documents from database AND disk
        def delete_selected():
            file_paths = []
            for idx in selected_indexes:
                item = self.active_documents_model.itemFromIndex(idx)
                if item:
                    file_path = item.data()
                    if file_path:
                        file_paths.append(file_path)

            for file_path in file_paths:
                # Delete from database
                docs = Document.objects.filter_by(path=file_path)
                if docs and len(docs) > 0:
                    Document.objects.delete(pk=docs[0].id)

                # Delete the actual file from disk
                try:
                    if os.path.exists(file_path):
                        os.remove(file_path)
                        fname = os.path.basename(file_path)
                        self.logger.info(
                            f"Deleted document from database and disk: {fname}"
                        )
                except Exception as e:
                    fname = os.path.basename(file_path)
                    self.logger.error(
                        f"Failed to delete file from disk {fname}: {e}"
                    )

            self.refresh_active_documents_list()
            self.emit_signal(SignalCode.DOCUMENT_COLLECTION_CHANGED)

        remove_action.triggered.connect(remove_selected)
        delete_action.triggered.connect(delete_selected)
        menu.addAction(remove_action)
        menu.addAction(delete_action)
        menu.exec(
            self.ui.activeDocumentsTreeView.viewport().mapToGlobal(position)
        )

    def show_unavailable_doc_context_menu(self, position):
        """Show context menu for unavailable documents."""
        index = self.ui.unavailableDocumentsTreeView.indexAt(position)
        if not index.isValid():
            return

        # Get all selected indexes
        selected_indexes = (
            self.ui.unavailableDocumentsTreeView.selectedIndexes()
        )
        if not selected_indexes:
            return

        menu = QMenu(self)

        # Show appropriate label based on selection count
        if len(selected_indexes) == 1:
            retry_action = QAction("Retry Indexing", self)
            delete_action = QAction("Delete", self)
        else:
            retry_action = QAction(
                f"Retry Indexing {len(selected_indexes)} Documents", self
            )
            delete_action = QAction(
                f"Delete {len(selected_indexes)} Documents", self
            )

        # Retry indexing selected documents - emit INDEX_DOCUMENT signal
        def retry_selected():
            file_paths = []
            for idx in selected_indexes:
                item = self.unavailable_documents_model.itemFromIndex(idx)
                if item:
                    file_path = item.data()
                    if file_path:
                        file_paths.append(file_path)

            # Emit INDEX_DOCUMENT signal for each file to trigger indexing
            # Do NOT mark as active yet - only mark as active if indexing succeeds
            for file_path in file_paths:
                self.emit_signal(
                    SignalCode.INDEX_DOCUMENT, {"path": file_path}
                )
                fname = os.path.basename(file_path)
                self.logger.info(f"Retrying indexing for: {fname}")

        # Delete selected documents from database AND disk
        def delete_selected():
            file_paths = []
            for idx in selected_indexes:
                item = self.unavailable_documents_model.itemFromIndex(idx)
                if item:
                    file_path = item.data()
                    if file_path:
                        file_paths.append(file_path)

            for file_path in file_paths:
                # Delete from database
                docs = Document.objects.filter_by(path=file_path)
                if docs and len(docs) > 0:
                    Document.objects.delete(pk=docs[0].id)

                # Delete the actual file from disk
                try:
                    if os.path.exists(file_path):
                        os.remove(file_path)
                        fname = os.path.basename(file_path)
                        self.logger.info(
                            f"Deleted document from database and disk: {fname}"
                        )
                except Exception as e:
                    fname = os.path.basename(file_path)
                    self.logger.error(
                        f"Failed to delete file from disk {fname}: {e}"
                    )

            self.refresh_active_documents_list()
            self.emit_signal(SignalCode.DOCUMENT_COLLECTION_CHANGED)

        retry_action.triggered.connect(retry_selected)
        delete_action.triggered.connect(delete_selected)
        menu.addAction(retry_action)
        menu.addAction(delete_action)
        menu.exec(
            self.ui.unavailableDocumentsTreeView.viewport().mapToGlobal(
                position
            )
        )

    def showEvent(self, event):
        super().showEvent(event)
        self.refresh_active_documents_list()
        # self._request_index_for_unindexed_documents()

    def on_document_collection_changed(self, data: dict):
        """Handle document collection changes from the worker."""
        self.refresh_active_documents_list()

    def _request_index_for_unindexed_documents(self):
        # Query all documents that are not indexed
        self._unindexed_docs = [
            doc.path
            for doc in Document.objects.filter(Document.indexed == False)
            if hasattr(doc, "path") and doc.path
        ]
        self._total_to_index = len(self._unindexed_docs)
        self._current_indexing = 0
        if self._total_to_index == 0:
            return
        self._index_next_document()

    def _index_next_document(self):
        if self._current_indexing < self._total_to_index:
            doc = self._unindexed_docs[self._current_indexing]
            self.emit_signal(SignalCode.INDEX_DOCUMENT, {"path": doc})

    def refresh_documents_list(self):
        self.documents_model.clear()
        doc_dir = self.documents_path
        if not os.path.exists(doc_dir):
            os.makedirs(doc_dir, exist_ok=True)
        for root, dirs, files in os.walk(doc_dir):
            for fname in sorted(files):
                ext = os.path.splitext(fname)[1][1:].lower()
                if ext in self.file_extensions and ext != "zim":
                    item = QStandardItem(fname)
                    item.setData(os.path.join(root, fname), Qt.UserRole)
                    self.documents_model.appendRow(item)

    def on_document_double_clicked(self, index):
        file_path = self.documents_model.data(index, Qt.UserRole)
        if file_path:
            self.on_file_open_requested({"file_path": file_path})
