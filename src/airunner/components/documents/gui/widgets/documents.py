from typing import Dict
import os
import shutil

from PySide6.QtGui import QStandardItemModel
from PySide6.QtCore import (
    Signal,
    Qt,
    QEvent,
    QFileSystemWatcher,
)
from PySide6.QtGui import (
    QIcon,
    QColor,
    QStandardItem,
    QAction,
)
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHeaderView,
    QMenu,
    QMessageBox,
    QTableWidgetItem,
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
from airunner.utils.path_policy import (
    PathPolicyError,
    resolve_existing_directory,
    resolve_existing_file,
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
        self._document_index_failures: dict[str, str] = {}
        self._pending_document_index_requests: dict[str, bool] = {}
        self.file_extensions = [
            "md",
            "txt",
            "docx",
            "doc",
            "odt",
            "mobi",
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
        self._document_fs_watcher = QFileSystemWatcher(self)
        self._document_fs_watcher.directoryChanged.connect(
            self._on_document_library_changed
        )
        self.knowledgeBasePanelWidget = self.ui.knowledge_base_panel_widget
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
        """Configure the table-only document management surface."""
        self._configure_documents_table()
        self.ui.documentsTableWidget.viewport().installEventFilter(self)

        # Load document state into the table.
        self.refresh_active_documents_list()
        self.refresh_documents_list()

    def _configure_documents_table(self) -> None:
        """Configure the sortable document status table."""
        table = self.ui.documentsTableWidget
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setAcceptDrops(True)
        table.setDragDropMode(QAbstractItemView.DragDropMode.DragDrop)
        table.setDragEnabled(True)
        table.setDefaultDropAction(Qt.DropAction.CopyAction)
        table.setSortingEnabled(True)
        table.verticalHeader().setVisible(False)
        header = table.horizontalHeader()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for column in range(1, table.columnCount()):
            header.setSectionResizeMode(
                column,
                QHeaderView.ResizeMode.ResizeToContents,
            )
        table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        table.customContextMenuRequested.connect(
            self.show_documents_table_context_menu
        )

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

    @property
    def zim_path(self) -> str:
        """Return the configured ZIM directory."""
        return os.path.join(
            os.path.expanduser(self.path_settings.base_path),
            "zim",
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
        activate_after_index = self._pending_document_index_requests.pop(
            document_path,
            None,
        )

        # Handle batch indexing counter
        if (
            self._total_to_index > 0
            and self._current_indexing < self._total_to_index
        ):
            self._current_indexing += 1
            self._index_next_document()

        if activate_after_index is False and document_path:
            docs = Document.objects.filter_by(path=document_path)
            if docs and len(docs) > 0:
                Document.objects.update(pk=docs[0].id, active=False)
        if document_path:
            self._document_index_failures.pop(document_path, None)

        # Refresh the document lists to show updated indexing status
        self.refresh_documents_list()

        # Log success
        if document_path:
            self.logger.info(f"Document indexed successfully: {display_name}")

    def on_document_index_failed(self, data: Dict):
        """Handle failed document indexing."""
        document_path = data.get("path", "")
        error = data.get("error", "Unknown error")
        deferred = bool(data.get("deferred"))
        display_name = (
            self._get_display_name(document_path) if document_path else ""
        )

        if document_path and not deferred:
            self._pending_document_index_requests.pop(document_path, None)
            self._document_index_failures[document_path] = error

        if document_path:
            if deferred:
                self.logger.info(
                    "Document indexing deferred for %s: %s",
                    display_name,
                    error,
                )
            else:
                self.logger.error(
                    f"Failed to index document {display_name}: {error}"
                )

        # Refresh the document lists - document should stay in unavailable
        self.refresh_documents_list()

    def eventFilter(self, obj, event):
        """Handle drag-and-drop events for the document status table."""
        if obj == self.ui.documentsTableWidget.viewport():
            if event.type() == QEvent.Type.DragEnter:
                event.acceptProposedAction()
                return True
            elif event.type() == QEvent.Type.Drop:
                self.handle_drop_on_documents_table(event)
                return True
        return super().eventFilter(obj, event)

    def on_available_doc_clicked(self, index):
        """Handle double-click on available documents to add to active list."""
        pass  # Single click does nothing, use drag-and-drop

    def handle_drop_on_documents_table(self, event):
        """Handle files dropped onto the document status table."""
        mime_data = event.mimeData()

        # Handle file paths from file system view
        handled = False

        # Standard file-system drags (URLs)
        if mime_data.hasUrls():
            for url in mime_data.urls():
                file_path = url.toLocalFile()
                if os.path.isfile(file_path):
                    self.add_document_to_active(file_path)
                elif os.path.isdir(file_path):
                    # Handle dropped folder - add all documents within it
                    self.add_folder_documents_to_active(file_path)
            handled = True

        if handled:
            event.acceptProposedAction()

    def add_folder_documents_to_active(self, folder_path: str):
        """Add all documents from a folder to the active RAG collection."""
        validated_folder = self._validate_document_directory(folder_path)
        if not validated_folder:
            return
        for root, dirs, files in os.walk(validated_folder):
            for fname in files:
                ext = os.path.splitext(fname)[1][1:].lower()
                if ext in self.file_extensions:
                    file_path = os.path.join(root, fname)
                    self.add_document_to_active(file_path)

    def index_folder_documents(
        self,
        folder_path: str,
        *,
        activate_after_index: bool = False,
    ) -> None:
        """Index all supported documents from a folder."""
        validated_folder = self._validate_document_directory(folder_path)
        if not validated_folder:
            return
        for root, dirs, files in os.walk(validated_folder):
            for fname in files:
                ext = os.path.splitext(fname)[1][1:].lower()
                if ext in self.file_extensions:
                    self._request_document_index(
                        os.path.join(root, fname),
                        activate_after_index=activate_after_index,
                    )

    def _request_document_index(
        self,
        file_path: str,
        *,
        activate_after_index: bool = False,
    ) -> bool:
        """Queue single-document indexing and record post-index intent."""
        validated_path = self._validate_document_file(file_path)
        if not validated_path:
            return False

        docs = Document.objects.filter_by(path=validated_path)
        if docs and docs[0].indexed:
            return False
        if not docs:
            Document.objects.create(
                path=validated_path,
                active=False,
                indexed=False,
            )

        pending = self._pending_document_index_requests.get(validated_path)
        if pending is not None:
            self._pending_document_index_requests[validated_path] = (
                pending or activate_after_index
            )
            return True

        failures = getattr(self, "_document_index_failures", None)
        if isinstance(failures, dict):
            failures.pop(validated_path, None)
        self._pending_document_index_requests[validated_path] = (
            activate_after_index
        )
        self.emit_signal(
            SignalCode.RAG_INDEX_SELECTED_DOCUMENTS,
            {"file_paths": [validated_path]},
        )
        return True

    def _refresh_document_watch_paths(self) -> None:
        """Watch current document directories for external file changes."""
        watcher = getattr(self, "_document_fs_watcher", None)
        if watcher is None:
            return

        desired_paths: set[str] = set()
        for root in (self.documents_path, self.zim_path):
            expanded_root = os.path.expanduser(root)
            if not os.path.isdir(expanded_root):
                continue
            desired_paths.add(expanded_root)
            for current_root, _dirs, _files in os.walk(expanded_root):
                desired_paths.add(current_root)

        existing_paths = set(watcher.directories())
        stale_paths = sorted(existing_paths - desired_paths)
        new_paths = sorted(desired_paths - existing_paths)
        if stale_paths:
            watcher.removePaths(stale_paths)
        if new_paths:
            watcher.addPaths(new_paths)

    def _on_document_library_changed(self, _path: str) -> None:
        """Refresh document views when files are changed outside the app."""
        self.refresh_documents_list()
        self.emit_signal(
            SignalCode.DOCUMENT_COLLECTION_CHANGED,
            {"reason": "filesystem"},
        )

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
        validated_path = self._validate_document_file(file_path)
        if not validated_path:
            return
        file_path = validated_path

        # Check if indexed
        docs = Document.objects.filter_by(path=file_path)
        if not docs or not docs[0].indexed:
            self._document_index_failures.pop(file_path, None)
            self._request_document_index(
                file_path,
                activate_after_index=True,
            )
            return

        if docs and getattr(docs[0], "active", False):
            self.logger.info(
                "Document already active: %s",
                self._get_display_name(file_path),
            )
            return
        display_name = self._get_display_name(file_path)

        # Update database
        if docs:
            Document.objects.update(pk=docs[0].id, active=True)
        else:
            Document.objects.create(path=file_path, active=True, indexed=True)

        self.logger.info(f"Added to active documents: {display_name}")
        self.refresh_active_documents_list()
        self.emit_signal(
            SignalCode.DOCUMENT_COLLECTION_CHANGED,
            {"paths": [file_path]},
        )

    def _validate_document_directory(self, folder_path: str) -> str | None:
        """Validate one directory before recursive document import."""
        try:
            return resolve_existing_directory(
                folder_path,
                label="Document directory",
                allowed_roots=self._allowed_document_roots(),
            )
        except PathPolicyError as error:
            self.logger.warning("Rejected document directory: %s", error)
            QMessageBox.warning(self, "Invalid Document Path", str(error))
            return None

    def _validate_document_file(self, file_path: str) -> str | None:
        """Validate one document file before using it in the UI."""
        suffixes = tuple(f".{ext}" for ext in self.file_extensions)
        try:
            return resolve_existing_file(
                file_path,
                label="Document path",
                allowed_suffixes=suffixes,
                allowed_roots=self._allowed_document_roots(),
            )
        except PathPolicyError as error:
            self.logger.warning("Rejected document path: %s", error)
            QMessageBox.warning(self, "Invalid Document Path", str(error))
            return None

    def _allowed_document_roots(self) -> tuple[str, str]:
        """Return the approved document roots for UI imports."""
        return (self.documents_path, self.zim_path)

    def remove_document_from_active(self, file_path: str):
        """Remove a document from the active RAG collection."""
        # Safety check
        if not file_path:
            self.logger.warning("Attempted to remove document with None path")
            return

        # Update database
        docs = Document.objects.filter_by(path=file_path)
        if docs and len(docs) > 0:
            Document.objects.update(pk=docs[0].id, active=False)

        display_name = self._get_display_name(file_path)
        self.logger.info(f"Removed from active documents: {display_name}")
        self.refresh_active_documents_list()
        self.emit_signal(
            SignalCode.DOCUMENT_COLLECTION_CHANGED,
            {"paths": [file_path]},
        )

    def _selected_document_table_paths(self) -> list[str]:
        """Return selected document paths from the status table."""
        table = getattr(self.ui, "documentsTableWidget", None)
        if table is None or table.selectionModel() is None:
            return []
        paths = []
        for index in table.selectionModel().selectedRows(0):
            item = table.item(index.row(), 0)
            path = item.data(Qt.ItemDataRole.UserRole) if item else None
            if isinstance(path, str):
                paths.append(path)
        return paths

    def _status_table_item(
        self,
        text: str = "",
        *,
        tooltip: str = "",
        color: str | None = None,
    ) -> QTableWidgetItem:
        """Return one centered, non-editable status cell."""
        item = QTableWidgetItem(text)
        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        if tooltip:
            item.setToolTip(tooltip)
        if color:
            item.setForeground(QColor(color))
        return item

    def _insert_document_table_row(self, row: int, document: Document) -> None:
        """Insert one document row into the status table."""
        table = self.ui.documentsTableWidget
        display_name = self._get_display_name(document.path)
        error_text = self._document_index_failures.get(document.path, "")
        title_item = QTableWidgetItem(display_name)
        title_item.setData(Qt.ItemDataRole.UserRole, document.path)
        title_item.setToolTip(document.path)
        title_item.setFlags(title_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        table.insertRow(row)
        table.setItem(row, 0, title_item)
        table.setItem(
            row,
            1,
            self._status_table_item(
                "✓" if document.active else "",
                color="#22c55e" if document.active else None,
            ),
        )
        table.setItem(
            row,
            2,
            self._status_table_item(
                "✓" if document.indexed else "",
                color="#22c55e" if document.indexed else None,
            ),
        )
        table.setItem(
            row,
            3,
            self._status_table_item(
                "✗" if error_text else "",
                tooltip=error_text,
                color="#ef4444" if error_text else None,
            ),
        )

    def refresh_active_documents_list(self):
        """Load all document states into the sortable status table."""
        table = getattr(self.ui, "documentsTableWidget", None)
        if table is None:
            return

        documents = [
            doc for doc in Document.objects.all() if os.path.exists(doc.path)
        ]
        documents.sort(key=lambda doc: self._get_display_name(doc.path).lower())
        self._document_index_failures = {
            path: error
            for path, error in self._document_index_failures.items()
            if os.path.exists(path)
        }

        table.setSortingEnabled(False)
        table.setRowCount(0)
        for document in documents:
            if document.indexed:
                self._document_index_failures.pop(document.path, None)
            self._insert_document_table_row(table.rowCount(), document)
        table.setSortingEnabled(True)

    def keyPressEvent(self, event):
        """Handle keyboard shortcuts for the document table."""
        if event.key() == Qt.Key.Key_Delete:
            if self.ui.documentsTableWidget.hasFocus():
                for file_path in self._selected_document_table_paths():
                    self.remove_document_from_active(file_path)
                return

        super().keyPressEvent(event)

    def show_documents_table_context_menu(self, position):
        """Show activation and indexing actions for the document table."""
        table = self.ui.documentsTableWidget
        if not table.indexAt(position).isValid():
            return

        selected_paths = self._selected_document_table_paths()
        if not selected_paths:
            return

        docs_by_path = {}
        for path in selected_paths:
            matches = Document.objects.filter_by(path=path)
            docs_by_path[path] = matches[0] if matches else None

        menu = QMenu(self)
        inactive_paths = [
            path
            for path, document in docs_by_path.items()
            if not getattr(document, "active", False)
        ]
        active_paths = [
            path
            for path, document in docs_by_path.items()
            if getattr(document, "active", False)
        ]
        unindexed_paths = [
            path
            for path, document in docs_by_path.items()
            if not getattr(document, "indexed", False)
        ]

        if inactive_paths:
            add_action = QAction("Add to Active Documents (RAG)", self)
            add_action.triggered.connect(
                lambda: [self.add_document_to_active(path) for path in inactive_paths]
            )
            menu.addAction(add_action)
        if active_paths:
            remove_action = QAction("Remove from Active Documents", self)
            remove_action.triggered.connect(
                lambda: [
                    self.remove_document_from_active(path)
                    for path in active_paths
                ]
            )
            menu.addAction(remove_action)
        if unindexed_paths:
            index_action = QAction("Index", self)
            index_action.triggered.connect(
                lambda: [self._request_document_index(path) for path in unindexed_paths]
            )
            menu.addAction(index_action)

        delete_action = QAction("Delete", self)

        def delete_selected():
            for file_path in selected_paths:
                self._document_index_failures.pop(file_path, None)
                docs = Document.objects.filter_by(path=file_path)
                if docs and len(docs) > 0:
                    Document.objects.delete(pk=docs[0].id)
                try:
                    if os.path.exists(file_path):
                        os.remove(file_path)
                except Exception as exc:
                    display_name = self._get_display_name(file_path)
                    self.logger.error(
                        "Failed to delete file from disk %s: %s",
                        display_name,
                        exc,
                    )

            self.refresh_documents_list()
            self.refresh_active_documents_list()
            self.emit_signal(SignalCode.DOCUMENT_COLLECTION_CHANGED)

        delete_action.triggered.connect(delete_selected)
        menu.addAction(delete_action)
        menu.exec(table.viewport().mapToGlobal(position))

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
                index_action = QAction("Index", self)
                delete_action = QAction("Delete", self)
            else:
                add_action = QAction(
                    "Add Folder to Active Documents (RAG)", self
                )
                index_action = QAction("Index Folder", self)
                delete_action = QAction("Delete Folder", self)
        else:
            add_action = QAction(
                f"Add {total_items} Items to Active (RAG)", self
            )
            index_action = QAction(f"Index {total_items} Items", self)
            delete_action = QAction(f"Delete {total_items} Items", self)

        # Add all selected files and folders
        def add_selected():
            for file_path in selected_files:
                self.add_document_to_active(file_path)
            for folder_path in selected_folders:
                self.add_folder_documents_to_active(folder_path)

        def index_selected():
            for file_path in selected_files:
                self._request_document_index(file_path)
            for folder_path in selected_folders:
                self.index_folder_documents(folder_path)

        # Delete selected files and folders from database AND disk
        def delete_selected():
            for file_path in selected_files:
                self._document_index_failures.pop(file_path, None)
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
                                self._document_index_failures.pop(
                                    file_path,
                                    None,
                                )
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
        index_action.triggered.connect(index_selected)
        delete_action.triggered.connect(delete_selected)
        menu.addAction(add_action)
        menu.addAction(index_action)
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
        self.refresh_documents_list()
        # self._request_index_for_unindexed_documents()

    def on_document_collection_changed(self, data: dict):
        """Handle document collection changes from the worker."""
        self.refresh_documents_list()

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
        """Refresh the table-driven document state and watcher roots."""
        self.refresh_active_documents_list()
        self._refresh_document_watch_paths()

    def _expand_available_document_sections(self, *items) -> None:
        """Expand populated document tree branches so imports are visible."""
        tree = getattr(getattr(self, "ui", None), "documentsTreeView", None)
        model = getattr(self, "documents_model", None)
        if tree is None or model is None:
            return

        for item in items:
            if item is None:
                continue
            try:
                should_expand = bool(item.rowCount())
            except Exception:
                should_expand = True
            if not should_expand:
                continue

            try:
                index = model.indexFromItem(item)
            except Exception:
                continue
            if hasattr(index, "isValid") and not index.isValid():
                continue
            tree.expand(index)

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
