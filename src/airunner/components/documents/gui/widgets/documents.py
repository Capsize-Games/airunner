from typing import Dict
import os
import re
import json
import pprint
import tempfile
import webbrowser
import urllib.parse
import datetime
import requests

from PySide6.QtCore import (
    Signal,
    Qt,
    QEvent,
    QObject,
    QTimer,
)
from PySide6.QtGui import (
    QIcon,
    QStandardItemModel,
    QStandardItem,
    QPixmap,
)
from PySide6.QtWidgets import (
    QFileSystemModel,
    QAbstractItemView,
    QListWidgetItem,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QMessageBox,
    QMenu,
    QAction,
    QFileDialog,
    QProgressDialog,
)

from airunner.enums import SignalCode
from airunner.utils.settings import get_qsettings
from airunner.utils.application.create_worker import create_worker
from airunner.components.application.gui.widgets.base_widget import BaseWidget
from airunner.components.documents.data.models.document import Document
from airunner.components.documents.data.scan_zimfiles import scan_zimfiles
from airunner.components.documents.data.models.zimfile import ZimFile
from airunner.components.documents.gui.widgets.templates.documents_ui import (
    Ui_documents,
)
from airunner.components.documents.kiwix_api import KiwixAPI


class DocumentsWidget(
    # SummarizationMixin,
    BaseWidget,
):
    """Widget that displays a file explorer for documents, reusing FileExplorerWidget."""

    titleChanged = Signal(str)
    urlChanged = Signal(str, str)  # url, title
    faviconChanged = Signal(QIcon)
    widget_class_ = Ui_documents
    zimDownloadFinished = Signal()

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
            "zim",  # Allow ZIM files
        ]
        self.signal_handlers = {
            SignalCode.DOCUMENT_INDEXED: self.on_document_indexed
        }
        super().__init__(*args, **kwargs)
        self.setup_file_explorer()
        self.setup_kiwix_browser()
        self.zimDownloadFinished.connect(self.refresh_kiwix_lists)

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

        # Enable custom drag and drop handling
        self.ui.documentsTreeView.setDefaultDropAction(
            Qt.DropAction.CopyAction
        )
        self.ui.activeDocumentsTreeView.viewport().installEventFilter(self)

        # Load active documents from database
        self.refresh_active_documents_list()

    def setup_kiwix_browser(self):
        # Use widgets from the .ui file for search controls and lists, now inside the ZIM tab
        self.tab_widget = self.ui.tabWidget
        self.local_zims_list = self.ui.listLocalZims
        self.search_results_list = self.ui.listRemoteZims
        self.kiwix_splitter = self.ui.splitter
        self.kiwix_search_bar = self.ui.kiwixSearchBar
        self.kiwix_lang_combo = self.ui.kiwixLangCombo
        self.kiwix_search_button = self.ui.kiwixSearchButton
        self.kiwix_search_bar.returnPressed.connect(
            self.on_kiwix_search_clicked
        )
        self.kiwix_search_button.clicked.connect(self.on_kiwix_search_clicked)
        self.kiwix_lang_combo.currentTextChanged.connect(
            self.refresh_kiwix_lists
        )
        self.show_local_zims_only = True
        self.refresh_kiwix_lists()

    def on_kiwix_search_clicked(self):
        self.show_local_zims_only = False
        self.refresh_kiwix_lists()

    def on_kiwix_search_changed(self, text):
        if not text.strip():
            self.show_local_zims_only = True
            self.refresh_kiwix_lists()

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
        self._current_indexing += 1
        self._index_next_document()

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
            event.acceptProposedAction()

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
        """Load active documents from database into the tree view."""
        self.active_documents_model.clear()

        # Get all active documents from database
        active_docs = Document.objects.filter(Document.active == True)

        for doc in active_docs:
            if os.path.exists(doc.path):
                filename = os.path.basename(doc.path)
                item = QStandardItem(filename)
                item.setData(doc.path)
                item.setEditable(False)

                # Show indexed status with icon or color
                if doc.indexed:
                    item.setToolTip(f"{filename}\n✓ Indexed and ready for RAG")
                else:
                    item.setToolTip(f"{filename}\n⚠ Not yet indexed")

                self.active_documents_model.appendRow(item)

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

        # Filter to only files (not directories)
        selected_files = []
        for idx in selected_indexes:
            file_path = self.documents_model.filePath(idx)
            if os.path.isfile(file_path):
                selected_files.append(file_path)

        if not selected_files:
            return

        menu = QMenu(self)

        # Show appropriate label based on selection count
        if len(selected_files) == 1:
            add_action = QAction("Add to Active Documents (RAG)", self)
        else:
            add_action = QAction(
                f"Add {len(selected_files)} Documents to Active", self
            )

        # Add all selected files
        def add_selected():
            for file_path in selected_files:
                self.add_document_to_active(file_path)

        add_action.triggered.connect(add_selected)
        menu.addAction(add_action)
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
        else:
            remove_action = QAction(
                f"Remove {len(selected_indexes)} Documents from Active", self
            )

        # Remove all selected documents
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

        remove_action.triggered.connect(remove_selected)
        menu.addAction(remove_action)
        menu.exec(
            self.ui.activeDocumentsTreeView.viewport().mapToGlobal(position)
        )

    def showEvent(self, event):
        super().showEvent(event)
        self._sync_documents_with_directory()
        self.refresh_active_documents_list()
        # self._request_index_for_unindexed_documents()

    def _sync_documents_with_directory(self):
        # Ensure every file in the watched directory and subdirectories has a Document entry
        doc_dir = self.documents_path
        if not os.path.exists(doc_dir):
            self.logger.error(f"Document directory does not exist: {doc_dir}")
            return
        for root, dirs, files in os.walk(doc_dir):
            for fname in files:
                fpath = os.path.join(root, fname)
                ext = os.path.splitext(fname)[1][1:].lower()
                if ext in self.file_extensions:
                    exists = Document.objects.filter_by(path=fpath)
                    if not exists or len(exists) == 0:
                        Document.objects.create(path=fpath, active=True)

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
            self.emit_signal(SignalCode.INDEX_DOCUMENT, {"path": doc})
        else:
            self._clear_progress_bar()

    def _clear_progress_bar(self):
        self.ui.progressBar.setValue(0)
        self.ui.progressBar.setFormat("")
        self.ui.progressBar.setVisible(False)

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

    def refresh_kiwix_lists(self):
        self.refresh_local_zims_list()
        self.refresh_search_results_list()

    def refresh_local_zims_list(self):
        zim_dir = os.path.join(
            os.path.expanduser(self.path_settings.base_path), "zim"
        )
        scan_zimfiles(zim_dir)
        self.local_zims_list.clear()
        local_zims = ZimFile.objects.all()

        def format_size(size):
            if not size or size <= 0:
                return "? MB"
            for unit in ["B", "KB", "MB", "GB", "TB"]:
                if size < 1024:
                    return (
                        f"{size:.1f} {unit}"
                        if unit != "B"
                        else f"{int(size)} {unit}"
                    )
                size /= 1024
            return f"{size:.1f} PB"

        for zim in sorted(local_zims, key=lambda z: z.name.lower()):
            meta = {
                "title": zim.title,
                "summary": zim.summary,
                "updated": zim.updated,
            }
            fname = zim.name
            fpath = zim.path
            size = zim.size
            row_widget = QWidget()
            row_layout = QVBoxLayout(row_widget)
            row_layout.setContentsMargins(6, 6, 6, 6)
            row_layout.setSpacing(2)
            top_row = QHBoxLayout()
            title = meta.get("title") or fname
            title_label = QLabel(f"<b>{title}</b>")
            title_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
            top_row.addWidget(title_label, 2)
            size_label = QLabel(
                f"<span style='color:gray'>({format_size(size)})</span>"
            )
            size_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
            top_row.addWidget(size_label, 0)
            if meta.get("updated"):
                date_label = QLabel(
                    f"<span style='color:gray'>{meta['updated']}</span>"
                )
                date_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
                top_row.addWidget(date_label, 0)
            top_row.addStretch(1)
            del_btn = QPushButton("Delete")
            del_btn.setFixedWidth(90)
            del_btn.clicked.connect(
                lambda _, f=fpath, n=fname: self.confirm_delete_zim(f, n)
            )
            top_row.addWidget(del_btn, 0)
            row_layout.addLayout(top_row)
            if meta.get("summary"):
                desc_label = QLabel(meta["summary"])
                desc_label.setWordWrap(True)
                desc_label.setStyleSheet("color: #555; font-size: 10pt;")
                desc_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
                row_layout.addWidget(desc_label)
            row_widget.setLayout(row_layout)
            item = QListWidgetItem()
            item.setSizeHint(row_widget.sizeHint())
            self.local_zims_list.addItem(item)
            self.local_zims_list.setItemWidget(item, row_widget)

    def refresh_search_results_list(self):
        self.search_results_list.clear()
        lang = (
            self.kiwix_lang_combo.currentText()
            if hasattr(self, "kiwix_lang_combo")
            else "eng"
        )
        if lang == "all":
            lang = None
        query = (
            self.kiwix_search_bar.text().strip()
            if hasattr(self, "kiwix_search_bar")
            else None
        )
        if not query:
            return
        zim_dir = os.path.join(
            os.path.expanduser(self.path_settings.base_path), "zim"
        )
        local_zims = {
            f for f in os.listdir(zim_dir) if f.lower().endswith(".zim")
        }
        try:
            zim_files = KiwixAPI.list_zim_files(language=lang, query=query)
            print("Kiwix API search results:")

            pprint.pprint(zim_files)
        except Exception as e:
            QMessageBox.critical(
                self, "Kiwix", f"Failed to fetch ZIM list: {e}"
            )
            return
        if not isinstance(zim_files, list):
            QMessageBox.critical(
                self, "Kiwix", "Invalid response from Kiwix API."
            )
            return
        local_zims = set()
        doc_dir = self.documents_path
        if os.path.exists(doc_dir):
            for f in os.listdir(doc_dir):
                if f.lower().endswith(".zim"):
                    local_zims.add(f)

        def format_size(size):
            if not size or size <= 0:
                return "? MB"
            for unit in ["B", "KB", "MB", "GB", "TB"]:
                if size < 1024:
                    return (
                        f"{size:.1f} {unit}"
                        if unit != "B"
                        else f"{int(size)} {unit}"
                    )
                size /= 1024
            return f"{size:.1f} PB"

        for zim in zim_files:
            name = zim.get("id") or zim.get("name") or zim.get("title")
            title = zim.get("title") or zim.get("name") or name
            size = zim.get("size")
            if size is None:
                summary = zim.get("summary", "")
                m = re.search(r"(\d+(?:\.\d+)?)\s*(MB|GB|GiB|MiB)", summary)
                if m:
                    val, unit = m.groups()
                    try:
                        val = float(val)
                        if unit in ("GB", "GiB"):
                            size = int(val * 1024 * 1024 * 1024)
                        else:
                            size = int(val * 1024 * 1024)
                    except Exception:
                        size = 0
                else:
                    size = 0
            desc = zim.get("description") or zim.get("summary") or ""
            url = zim.get("url")
            if not url and "links" in zim:
                for link in zim["links"]:
                    href = link.get("href")
                    if (
                        link.get("rel") == "enclosure"
                        and href
                        and href.endswith(".zim")
                    ):
                        url = href
                        break
            # If url is relative, prepend Kiwix base
            if url and url.startswith("/"):
                url = urllib.parse.urljoin("https://library.kiwix.org", url)
            is_downloaded = name in local_zims
            updated = zim.get("updated") or zim.get("date")
            if updated:
                try:
                    updated = str(
                        datetime.datetime.fromisoformat(
                            updated.replace("Z", "+00:00")
                        ).date()
                    )
                except Exception:
                    updated = str(updated)
            # Build custom widget for row
            row_widget = QWidget()
            row_layout = QVBoxLayout(row_widget)
            row_layout.setContentsMargins(6, 6, 6, 6)
            row_layout.setSpacing(2)
            # Illustration image row
            img_url = zim.get("url")
            if img_url and "/illustration/" in img_url:
                # Fix double https:// if present
                if img_url.startswith("//"):
                    img_url = "https:" + img_url
                elif img_url.startswith("/catalog/"):
                    img_url = "https://library.kiwix.org" + img_url
                try:
                    cache_dir = tempfile.gettempdir()
                    img_cache_path = os.path.join(
                        cache_dir, os.path.basename(img_url)
                    )
                    if not os.path.exists(img_cache_path):
                        r = requests.get(img_url, timeout=10)
                        if r.status_code == 200:
                            with open(img_cache_path, "wb") as f:
                                f.write(r.content)
                    pixmap = QPixmap(img_cache_path)
                    if not pixmap.isNull():
                        img_label = QLabel()
                        img_label.setPixmap(pixmap.scaledToHeight(48))
                        row_layout.addWidget(img_label, alignment=Qt.AlignLeft)
                except Exception:
                    pass
            # Title and size row
            top_row = QHBoxLayout()
            title_label = QLabel(f"<b>{title}</b>")
            title_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
            top_row.addWidget(title_label, 2)
            size_label = QLabel(
                f"<span style='color:gray'>({format_size(size)})</span>"
            )
            size_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
            top_row.addWidget(size_label, 0)
            if updated:
                date_label = QLabel(
                    f"<span style='color:gray'>{updated}</span>"
                )
                date_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
                top_row.addWidget(date_label, 0)
            top_row.addStretch(1)
            if is_downloaded:
                downloaded_label = QLabel(
                    "<span style='color:green'>[Downloaded]</span>"
                )
                top_row.addWidget(downloaded_label, 0)
            elif url and url.endswith(".zim") and url.startswith("http"):
                btn = QPushButton("Download")
                btn.setFixedWidth(90)
                btn.clicked.connect(
                    lambda _, z=zim: self.download_kiwix_zim(
                        {**zim, "url": url}
                    )
                )
                top_row.addWidget(btn, 0)
            else:
                search_btn = QPushButton("Search on Kiwix.org")
                search_btn.setFixedWidth(150)
                search_btn.clicked.connect(
                    lambda _, t=title: self.open_kiwix_search(t)
                )
                top_row.addWidget(search_btn, 0)
            row_layout.addLayout(top_row)
            # Description row
            if desc:
                desc_label = QLabel(desc)
                desc_label.setWordWrap(True)
                desc_label.setStyleSheet("color: #555; font-size: 10pt;")
                desc_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
                row_layout.addWidget(desc_label)
            row_widget.setLayout(row_layout)
            item = QListWidgetItem()
            item.setSizeHint(row_widget.sizeHint())
            self.search_results_list.addItem(item)
            self.search_results_list.setItemWidget(item, row_widget)

    def open_kiwix_search(self, title):
        # Open the Kiwix download search page for the title
        url = f"https://library.kiwix.org/?q={urllib.parse.quote(title)}"
        webbrowser.open(url)

    def download_kiwix_zim(self, zim):
        name = zim.get("id") or zim.get("name") or zim.get("title")
        url = zim.get("url")
        if not url:
            QMessageBox.warning(self, "Kiwix", f"No download URL for {name}")
            return
        zim_dir = os.path.join(
            os.path.expanduser(self.path_settings.base_path), "zim"
        )
        if not os.path.exists(zim_dir):
            os.makedirs(zim_dir, exist_ok=True)
        save_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save ZIM File",
            os.path.join(zim_dir, f"{name}.zim"),
            "ZIM Files (*.zim)",
        )
        if not save_path:
            return
        meta_path = save_path + ".json"
        progress_dialog = QProgressDialog(
            f"Downloading {name}...", "Cancel", 0, 100, self
        )
        progress_dialog.setWindowTitle("Downloading ZIM File")
        progress_dialog.setWindowModality(Qt.ApplicationModal)
        progress_dialog.setMinimumDuration(0)
        progress_dialog.setValue(0)
        progress_dialog.setAutoClose(False)
        progress_dialog.setAutoReset(False)

        class DownloadWorker(QObject):
            finished = Signal(bool, object)
            # Use object type for consistency across download progress signals.
            progress = Signal(object)

            def __init__(self, url, save_path):
                super().__init__()
                self.url = url
                self.save_path = save_path
                self._abort = False

            def run(self):
                try:
                    with requests.get(self.url, stream=True, timeout=60) as r:
                        r.raise_for_status()
                        total = int(r.headers.get("content-length", 0))
                        downloaded = 0
                        with open(self.save_path, "wb") as f:
                            for chunk in r.iter_content(chunk_size=8192):
                                if self._abort:
                                    self.finished.emit(
                                        False, "Download cancelled"
                                    )
                                    return
                                if chunk:
                                    f.write(chunk)
                                    downloaded += len(chunk)
                                    percent = (
                                        int(downloaded * 100 / total)
                                        if total
                                        else 0
                                    )
                                    self.progress.emit(percent)
                    self.finished.emit(True, None)
                except Exception as e:
                    self.finished.emit(False, str(e))

            def abort(self):
                self._abort = True

        worker = create_worker(DownloadWorker, url=url, save_path=save_path)

        def on_progress(val):
            progress_dialog.setValue(val)

        def on_finished(success, error=None):
            # Ensure the progress dialog is closed and deleted
            progress_dialog.reset()
            progress_dialog.deleteLater()
            if success:
                try:
                    with open(meta_path, "w", encoding="utf-8") as mf:
                        json.dump(zim, mf, ensure_ascii=False, indent=2)
                except Exception:
                    pass
                self.zimDownloadFinished.emit()
            else:
                QMessageBox.critical(
                    self, "Kiwix", f"Download failed: {error}"
                )

        worker.progress.connect(on_progress)
        worker.finished.connect(on_finished)
        progress_dialog.canceled.connect(worker.abort)
        progress_dialog.show()

    def confirm_delete_zim(self, fpath, fname):
        reply = QMessageBox.question(
            self,
            "Delete ZIM File",
            f"Are you sure you want to delete '{fname}'?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            try:
                os.remove(fpath)
                meta_path = fpath + ".json"
                if os.path.exists(meta_path):
                    os.remove(meta_path)
                QTimer.singleShot(0, self.refresh_kiwix_lists)
            except Exception as e:
                QMessageBox.critical(
                    self, "Error", f"Failed to delete file: {e}"
                )
