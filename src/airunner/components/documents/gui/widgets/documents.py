from airunner.components.documents.gui.widgets.templates.documents_ui import (
    Ui_documents,
)

from airunner.gui.widgets.base_widget import BaseWidget
from PySide6.QtCore import Signal, Qt, Slot
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
from airunner.utils.os.find_files import find_files


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
    files_found = Signal(list)

    def __init__(self, *args, private: bool = False, **kwargs):
        self._favicon = None
        self._private = private
        super().__init__(*args, **kwargs)
        self.files_found.connect(self._add_document_widgets_from_files)
        self.setup_documents_list()
        self.load_documents()

    @Slot()
    def on_browse_button_clicked(self):
        # open a directory browser
        dir_path = QFileDialog.getExistingDirectory(
            self,
            "Select Document Folder",
            os.path.expanduser("~/Documents"),
        )
        if dir_path:
            self.ui.path.setText(dir_path)

    @Slot(str)
    def on_path_textChanged(self, text: str):
        self.clear_documents()
        if os.path.exists(text):
            self.load_documents()

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

        def handle_files(file_paths):
            print(
                f"handle_files called with {len(file_paths)} files: {file_paths[:5]} ..."
            )
            self.files_found.emit(file_paths)

        # Use filesystem instead of database
        find_files(
            path=self.ui.path.text() or "~/Documents",
            file_extension=["md", "txt", "docx", "doc", "odt", "pdf"],
            recursive=True,
            callback=handle_files,
        )

    @Slot(list)
    def _add_document_widgets_from_files(self, file_paths):
        print("_add_document_widgets_from_files called")
        for path in file_paths:
            print(f"add_document_widget called for: {path}")
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
        # Ensure DocumentWidget has no parent so it embeds in the list, not as a window
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
        doc = Document.objects.get(id=document.id)
        if doc:
            Document.objects.delete(doc.id, private=self._private)
        # Remove from list_widget (only from UI, not from disk)
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            widget = self.list_widget.itemWidget(item)
            if (
                hasattr(widget, "document")
                and widget.document.id == document.id
            ):
                self.list_widget.takeItem(i)
                break

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
