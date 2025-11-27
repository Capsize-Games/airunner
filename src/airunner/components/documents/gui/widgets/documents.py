from typing import Dict
import os
import shutil

from PySide6.QtGui import QStandardItemModel
from PySide6.QtCore import (
    Signal,
    Qt,
    QEvent,
)
from PySide6.QtGui import (
    QIcon,
    QStandardItem,
    QAction,
)
from PySide6.QtWidgets import (
    QAbstractItemView,
    QMenu,
    QMessageBox,
)

from airunner.enums import SignalCode
from airunner.utils.settings import get_qsettings
from airunner.components.application.gui.widgets.base_widget import BaseWidget
from airunner.components.documents.data.models.document import Document
from airunner.components.documents.data.models.zimfile import ZimFile
from airunner.components.documents.gui.widgets.templates.documents_ui import (
    Ui_documents,
)
from airunner.components.documents.gui.widgets.kiwix_widget import KiwixWidget
from airunner.components.file_explorer.gui.widgets.file_explorer_widget import (
    FileExplorerWidget,
)


class DocumentsWidget(BaseWidget):
    """Widget for document management and file exploration."""

    titleChanged = Signal(str)
    urlChanged = Signal(str, str)
    faviconChanged = Signal(QIcon)
    widget_class_ = Ui_documents

    def __init__(self, *args, private: bool = False, **kwargs):
        self._favicon = None
        self._private = private
        self._current_indexing = 0
        self._total_to_index = 0
        self._unindexed_docs = []
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
            SignalCode.RAG_INDEXING_COMPLETE: self.on_indexing_complete,
        }
        super().__init__(*args, **kwargs)
        self.setup_file_explorer()
        self.kiwix_widget = KiwixWidget()
        self.setup_kiwix_widget()
        self.setup_knowledge_folder()

    def setup_knowledge_folder(self):
        """Setup the knowledge folder file explorer in the Knowledge tab."""
        # Get the knowledge folder path
        knowledge_path = os.path.join(
            os.path.expanduser(self.path_settings.base_path),
            f"knowledge",
        )

        # Create the directory if it doesn't exist
        if not os.path.exists(knowledge_path):
            os.makedirs(knowledge_path, exist_ok=True)

        # Create the file explorer widget
        self.knowledge_file_explorer = FileExplorerWidget(
            path_to_display=knowledge_path,
            parent=self.ui.knowledgeFolderContainer,
        )

        # Add it to the container layout
        self.ui.knowledgeFolderLayout.addWidget(self.knowledge_file_explorer)

    def setup_file_explorer(self):
        # Setup available documents tree (use a QStandardItemModel so we can
        # inject a virtual "Kiwix Zim Files" folder without creating it on
        # disk). We'll list local documents from `documents_path` and add a
        # top-level virtual folder for ZIM files stored in the ZimFile model.
        self.documents_model = QStandardItemModel(self)
        self.ui.documentsTreeView.setModel(self.documents_model)
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

        # Load active documents from database and populate available list
        self.refresh_active_documents_list()
        self.refresh_documents_list()

    def setup_kiwix_widget(self):
        """Initialize the Kiwix widget with UI components."""
        self.kiwix_widget.initialize(
            local_zims_list=self.ui.listLocalZims,
            search_results_list=self.ui.listRemoteZims,
            kiwix_search_bar=self.ui.kiwixSearchBar,
            kiwix_lang_combo=self.ui.kiwixLangCombo,
            kiwix_search_button=self.ui.kiwixSearchButton,
        )
        # When a ZIM download finishes, refresh the available documents list
        try:
            self.kiwix_widget.zimDownloadFinished.connect(
                self.refresh_documents_list
            )
        except Exception:
            pass

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
        # base_path now auto-resolves via hybrid_property
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
        document_path = data.get("path", "")
        display_name = (
            self._get_display_name(document_path) if document_path else ""
        )

        # Handle batch indexing counter
        if (
            self._total_to_index > 0
            and self._current_indexing < self._total_to_index
        ):
            self._current_indexing += 1
            self._index_next_document()

        # Refresh the document lists to show updated indexing status
        self.refresh_active_documents_list()

        # Log success
        if document_path:
            self.logger.info(f"Document indexed successfully: {display_name}")

    def on_document_index_failed(self, data: Dict):
        """Handle failed document indexing."""
        document_path = data.get("path", "")
        error = data.get("error", "Unknown error")
        display_name = (
            self._get_display_name(document_path) if document_path else ""
        )

        if document_path:
            self.logger.error(
                f"Failed to index document {display_name}: {error}"
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
        handled = False

        # 1) Standard file-system drags (URLs)
        if mime_data.hasUrls():
            for url in mime_data.urls():
                file_path = url.toLocalFile()
                if os.path.isfile(file_path):
                    self.add_document_to_active(file_path)
                elif os.path.isdir(file_path):
                    # Handle dropped folder - add all documents within it
                    self.add_folder_documents_to_active(file_path)
            handled = True

        # 2) Drags from our own documentsTreeView which uses QStandardItemModel
        # Extract source widget and if it's the documentsTreeView, pull selected
        # items and add their stored paths (Qt.UserRole)
        try:
            src = event.source()
            if src is self.ui.documentsTreeView:
                sel = src.selectedIndexes()
                for idx in sel:
                    item = self.documents_model.itemFromIndex(idx)
                    if not item:
                        continue
                    # If it's a folder node, expand children
                    if item.hasChildren():
                        for r in range(item.rowCount()):
                            child = item.child(r, 0)
                            if child:
                                data = child.data(Qt.UserRole)
                                if isinstance(data, str):
                                    if os.path.isfile(data):
                                        self.add_document_to_active(data)
                    else:
                        data = item.data(Qt.UserRole)
                        if isinstance(data, str):
                            if os.path.isfile(data):
                                self.add_document_to_active(data)
                handled = True
        except Exception:
            # Fall back silently to URL handling
            pass

        if handled:
            event.acceptProposedAction()

    def add_folder_documents_to_active(self, folder_path: str):
        """Add all documents from a folder to the active RAG collection."""
        for root, dirs, files in os.walk(folder_path):
            for fname in files:
                ext = os.path.splitext(fname)[1][1:].lower()
                if ext in self.file_extensions:
                    file_path = os.path.join(root, fname)
                    self.add_document_to_active(file_path)

    def _get_display_name(self, file_path: str) -> str:
        """Get human-readable display name for a file.

        For ZIM files, returns the title from metadata if available.
        For other files, returns the filename.

        Args:
            file_path: Full path to the file

        Returns:
            Display name for the file
        """
        filename = os.path.basename(file_path)

        # Check if this is a ZIM file
        if filename.lower().endswith(".zim"):
            # Look up ZIM metadata from database
            zim_records = ZimFile.objects.filter_by(path=file_path)
            if zim_records and len(zim_records) > 0:
                zim = zim_records[0]
                # Return title if available, otherwise filename
                if zim.title:
                    return zim.title

        return filename

    def add_document_to_active(self, file_path: str):
        """Add a document to the active RAG collection."""
        # Check if indexed
        docs = Document.objects.filter_by(path=file_path)
        if not docs or not docs[0].indexed:
            QMessageBox.information(
                self,
                "Cannot Add",
                f"Document {self._get_display_name(file_path)} is not indexed yet. Please index it first.",
            )
            return

        # Check if already in active list
        for row in range(self.active_documents_model.rowCount()):
            item = self.active_documents_model.item(row, 0)
            if item and item.data() == file_path:
                self.logger.info(
                    f"Document already active: {self._get_display_name(file_path)}"
                )
                return

        # Add to model with display name
        display_name = self._get_display_name(file_path)
        item = QStandardItem(display_name)
        item.setData(file_path)
        item.setEditable(False)
        self.active_documents_model.appendRow(item)

        # Update database
        if docs:
            Document.objects.update(pk=docs[0].id, active=True)
        else:
            Document.objects.create(path=file_path, active=True, indexed=True)

        self.logger.info(f"Added to active documents: {display_name}")

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

        display_name = self._get_display_name(file_path)
        self.logger.info(f"Removed from active documents: {display_name}")

    def refresh_active_documents_list(self):
        """Load active and unavailable documents from database into the tree views."""
        self.active_documents_model.clear()
        self.unavailable_documents_model.clear()

        # Get all documents from database
        all_docs = Document.objects.all()

        for doc in all_docs:
            if not os.path.exists(doc.path):
                continue

            display_name = self._get_display_name(doc.path)
            item = QStandardItem(display_name)
            item.setData(doc.path)
            item.setEditable(False)

            # Determine which list to add to
            if doc.active and doc.indexed:
                # Active and indexed - add to active list
                item.setToolTip(f"{display_name}\n✓ Indexed and ready for RAG")
                self.active_documents_model.appendRow(item)
            elif doc.active and not doc.indexed:
                # Active but not indexed - try to index
                # If it repeatedly fails to index, it might be unavailable
                # For now, keep it in active list with warning
                item.setToolTip(f"{display_name}\n⚠ Not yet indexed")
                self.active_documents_model.appendRow(item)
            elif not doc.active and not doc.indexed:
                # Not active and not indexed - reserved for failed indexing attempts
                # For now, don't show new unindexed documents here
                pass

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

        # Collect files and folders from the QStandardItemModel. The model
        # stores file paths in Qt.UserRole. We also support a virtual
        # "Kiwix Zim Files" parent which contains child items with paths.
        selected_files = []
        selected_folders = []
        selected_folder_items = []
        for idx in selected_indexes:
            item = self.documents_model.itemFromIndex(idx)
            if item is None:
                continue
            # If the item has an explicit directory path stored, treat it as a folder
            data = item.data(Qt.UserRole)
            if isinstance(data, str) and os.path.isdir(data):
                # This is a real folder on disk
                selected_folders.append(data)
                continue

            # If the item has children, treat it as a (possibly virtual) folder
            if item.hasChildren():
                # If folder node stores a path, prefer that
                if isinstance(data, str) and data:
                    selected_folders.append(data)
                else:
                    selected_folder_items.append(item)
                continue

            # Otherwise, treat it as a file-like item
            if isinstance(data, str):
                selected_files.append(data)

        # Expand folder items into their child paths
        for folder_item in selected_folder_items:
            for r in range(folder_item.rowCount()):
                child = folder_item.child(r, 0)
                if child is None:
                    continue
                data = child.data(Qt.UserRole)
                if isinstance(data, str):
                    selected_files.append(data)

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
                        display_name = self._get_display_name(file_path)
                        self.logger.info(
                            f"Deleted document from database and disk: {display_name}"
                        )
                except Exception as e:
                    display_name = self._get_display_name(file_path)
                    self.logger.error(
                        f"Failed to delete file from disk {display_name}: {e}"
                    )

            for folder_path in selected_folders:
                # Delete all documents in the folder from database and disk
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
                        display_name = self._get_display_name(file_path)
                        self.logger.info(
                            f"Deleted document from database and disk: {display_name}"
                        )
                except Exception as e:
                    display_name = self._get_display_name(file_path)
                    self.logger.error(
                        f"Failed to delete file from disk {display_name}: {e}"
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

        # Retry indexing selected documents - delegate to knowledge base panel
        def retry_selected():
            file_paths = []
            for idx in selected_indexes:
                item = self.unavailable_documents_model.itemFromIndex(idx)
                if item:
                    file_path = item.data()
                    if file_path:
                        file_paths.append(file_path)

            if not file_paths:
                return

            # Emit signal to knowledge base panel to handle indexing
            # This uses the same threaded approach as "Index All" which doesn't freeze
            self.logger.info(
                f"Requesting reindex for {len(file_paths)} documents"
            )
            self.emit_signal(
                SignalCode.RAG_INDEX_SELECTED_DOCUMENTS,
                {"file_paths": file_paths},
            )

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
                        display_name = self._get_display_name(file_path)
                        self.logger.info(
                            f"Deleted document from database and disk: {display_name}"
                        )
                except Exception as e:
                    display_name = self._get_display_name(file_path)
                    self.logger.error(
                        f"Failed to delete file from disk {display_name}: {e}"
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
        print("ON DOCUMENT COLLECTION CHANGED: documents.py")
        """Handle document collection changes from the worker."""
        self.refresh_documents_list()
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
        """Rebuild the available documents model.

        Structure:
          - Indexed
            - Local (mirrors folders from documents_path)
            - Zim (ZimFile entries that are indexed)
          - Unindexed
            - Local
            - Zim
        """
        self.documents_model.clear()

        # Top-level containers
        indexed = QStandardItem("Indexed")
        indexed.setEditable(False)
        unindexed = QStandardItem("Unindexed")
        unindexed.setEditable(False)

        indexed_local = QStandardItem("Local")
        indexed_local.setEditable(False)
        indexed_zim = QStandardItem("Zim")
        indexed_zim.setEditable(False)

        unindexed_local = QStandardItem("Local")
        unindexed_local.setEditable(False)
        unindexed_zim = QStandardItem("Zim")
        unindexed_zim.setEditable(False)

        indexed.appendRow(indexed_local)
        indexed.appendRow(indexed_zim)
        unindexed.appendRow(unindexed_local)
        unindexed.appendRow(unindexed_zim)

        def is_indexed(path: str) -> bool:
            try:
                docs = Document.objects.filter_by(path=path)
                if docs and len(docs) > 0:
                    return bool(docs[0].indexed)
            except Exception:
                pass
            return False

        # Populate local files (preserve folder structure)
        doc_dir = self.documents_path
        if not os.path.exists(doc_dir):
            os.makedirs(doc_dir, exist_ok=True)

        folder_map_indexed = {"": indexed_local}
        folder_map_unindexed = {"": unindexed_local}

        for root, dirs, files in os.walk(doc_dir):
            rel_root = os.path.relpath(root, doc_dir)
            if rel_root == ".":
                rel_root = ""

            for fname in sorted(files):
                ext = os.path.splitext(fname)[1][1:].lower()
                if ext not in self.file_extensions:
                    continue
                full_path = os.path.join(root, fname)
                target_indexed = is_indexed(full_path)

                folder_map = (
                    folder_map_indexed
                    if target_indexed
                    else folder_map_unindexed
                )
                target_root = rel_root

                if target_root not in folder_map:
                    parts = target_root.split(os.sep) if target_root else []
                    cur = ""
                    parent_item = (
                        indexed_local if target_indexed else unindexed_local
                    )
                    for p in parts:
                        cur = os.path.join(cur, p) if cur else p
                        if cur not in folder_map:
                            node = QStandardItem(p)
                            node.setEditable(False)
                            node.setData(
                                os.path.join(doc_dir, cur), Qt.UserRole
                            )
                            parent_item.appendRow(node)
                            folder_map[cur] = node
                            parent_item = node
                        else:
                            parent_item = folder_map[cur]

                parent = folder_map.get(
                    target_root,
                    indexed_local if target_indexed else unindexed_local,
                )
                file_item = QStandardItem(self._get_display_name(full_path))
                file_item.setEditable(False)
                file_item.setData(full_path, Qt.UserRole)
                parent.appendRow(file_item)

        # Populate ZIM files into Zim subtrees
        try:
            local_zim_names = set()
            zim_dir = os.path.join(
                os.path.expanduser(self.path_settings.base_path), "zim"
            )
            if os.path.exists(zim_dir):
                for f in os.listdir(zim_dir):
                    if f.lower().endswith(".zim"):
                        local_zim_names.add(f)

            for zim in ZimFile.objects.all():
                display = zim.title or zim.name or os.path.basename(zim.path)
                item = QStandardItem(display)
                item.setEditable(False)
                item.setData(zim.path, Qt.UserRole)
                tip = f"{display}\n{zim.summary or ''}".strip()
                if os.path.basename(zim.path) in local_zim_names:
                    tip += "\n✓ Downloaded"
                item.setToolTip(tip)
                if is_indexed(zim.path):
                    indexed_zim.appendRow(item)
                else:
                    unindexed_zim.appendRow(item)
        except Exception:
            pass

        # Append to model
        self.documents_model.appendRow(indexed)
        self.documents_model.appendRow(unindexed)

    def on_document_double_clicked(self, index):
        item = self.documents_model.itemFromIndex(index)
        if item is None:
            return
        file_path = item.data(Qt.UserRole)
        if file_path:
            self.on_file_open_requested({"file_path": file_path})

    def on_indexing_complete(self, data: dict):
        """Handle indexing completion - refresh lists to move indexed docs."""
        self.refresh_documents_list()
        self.refresh_active_documents_list()
