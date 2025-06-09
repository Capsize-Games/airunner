from airunner.components.documents.gui.widgets.templates.documents_ui import (
    Ui_documents,
)

from airunner.gui.widgets.base_widget import BaseWidget
from PySide6.QtCore import Signal, Qt, Slot, QFileSystemWatcher, QFile
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QFileDialog
from PySide6.QtWidgets import (
    QListWidgetItem,
    QAbstractItemView,
)
from airunner.components.documents.data.models.document import Document
from airunner.components.documents.gui.widgets.document_widget import (
    DocumentWidget,
)
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
    """Widget that displays a single browser instance (address bar, navigation, webview, etc.).

    Inherits mixins for modular browser logic.
    """

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
        super().__init__(*args, **kwargs)
        self.setup_documents_list()
        self._setup_filesystem_watcher()
        self.load_documents()

    @Slot()
    def on_add_files_clicked(self):
        options = QFileDialog.Options()
        options |= QFileDialog.ReadOnly
        filter_str = f"Documents ({' '.join(['*.' + ext for ext in self.file_extensions])})"
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Add Files",
            "",
            filter_str,
            options=options,
        )
        if files:
            self._add_files(files)

    def _add_files(self, files):
        for file_path in files:
            base_name = os.path.basename(file_path)
            dest_path = os.path.join(self.documents_path, base_name)
            name, ext = os.path.splitext(base_name)
            n = 1
            # Find a unique filename if needed
            while os.path.exists(dest_path):
                dest_path = os.path.join(
                    self.documents_path, f"{name}_{n}{ext}"
                )
                n += 1
            QFile.copy(file_path, dest_path)

    def _setup_filesystem_watcher(self):
        self.fs_watcher = QFileSystemWatcher(self)
        self.fs_watcher.addPath(self.documents_path)
        self.fs_watcher.directoryChanged.connect(
            self._on_documents_dir_changed
        )

    def _on_documents_dir_changed(self, path):
        self.load_documents()

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
        # Update watcher if path changes
        if hasattr(self, "fs_watcher"):
            self.fs_watcher.removePaths(self.fs_watcher.directories())
            self.fs_watcher.addPath(value)

    def setup_documents_list(self):
        # Use the QListWidget from the template, not a new one
        self.list_widget = self.ui.document_list
        self.list_widget.setSelectionMode(
            QAbstractItemView.SelectionMode.NoSelection
        )
        self.list_widget.setAcceptDrops(True)
        self.list_widget.setDragDropMode(
            QAbstractItemView.DragDropMode.DropOnly
        )
        self.list_widget.viewport().setAcceptDrops(True)
        self.list_widget.setDefaultDropAction(Qt.DropAction.CopyAction)
        self.list_widget.dragEnterEvent = self.dragEnterEvent
        self.list_widget.dropEvent = self.dropEvent

    def clear_documents(self):
        """Clear the document list widget."""
        self.list_widget.clear()
        # Optionally clear the database or cache if needed
        # Document.objects.clear(private=self._private)

    def load_documents(self):
        self.list_widget.clear()

        # Clean up database: remove documents whose paths no longer exist
        for document in Document.objects.all():
            if not os.path.exists(document.path):
                Document.objects.delete(document.id)

        # List files in the documents directory with allowed extensions
        file_paths = []
        for root, dirs, files in os.walk(self.documents_path):
            for file in files:
                ext = os.path.splitext(file)[1][1:].lower()
                if ext in self.file_extensions:
                    file_paths.append(os.path.join(root, file))
        self._add_document_widgets_from_files(file_paths)

    @Slot(list)
    def _add_document_widgets_from_files(self, file_paths):
        for path in file_paths:
            self._add_document_widget(path)

    def _add_document_widget(self, path):
        # Create a simple document object with .path and .active attributes
        class Doc:
            def __init__(self, path):
                self.path = path
                self.active = False

        doc = Doc(path)
        widget = DocumentWidget(
            doc,
            on_active_changed=self.on_active_changed,
            parent=self.list_widget,
        )
        # Do NOT set window flags here; let QWidget default flags apply
        if widget.parent() is not self.list_widget:
            widget.setParent(self.list_widget)
        widget.delete_requested.connect(self.on_delete_document)
        item = QListWidgetItem(self.list_widget)
        item.setSizeHint(widget.sizeHint())
        self.list_widget.addItem(item)
        self.list_widget.setItemWidget(item, widget)

    def add_document_item(self, document):
        widget = DocumentWidget(
            document,
            on_active_changed=self.on_active_changed,
            parent=self.list_widget,
        )
        if widget.parent() is not self.list_widget:
            widget.setParent(self.list_widget)
        widget.delete_requested.connect(self.on_delete_document)
        item = QListWidgetItem(self.list_widget)
        item.setSizeHint(widget.sizeHint())
        self.list_widget.addItem(item)
        self.list_widget.setItemWidget(item, widget)

    def on_delete_document(self, document):
        # No longer needed: file/database deletion is handled in DocumentWidget, and UI updates via directory watcher
        pass

    def on_active_changed(self, document, active):
        Document.objects.update(
            document.id, active=active, private=self._private
        )

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if not path or not os.path.isfile(path):
                continue
            exists = Document.objects.filter_by(path=path)
            if not exists:
                doc = Document.objects.create(path=path, active=True)
                self.add_document_item(doc)
        event.acceptProposedAction()
