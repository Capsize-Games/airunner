from airunner.components.documents.gui.widgets.templates.documents_ui import (
    Ui_documents,
)

from airunner.gui.widgets.base_widget import BaseWidget
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QListWidget,
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
        super().__init__(*args, **kwargs)
        self.setup_documents_list()
        self.load_documents()

    def setup_documents_list(self):
        self.list_widget = QListWidget(self)
        self.list_widget.setSelectionMode(
            QAbstractItemView.SelectionMode.NoSelection
        )
        self.list_widget.setAcceptDrops(True)
        self.list_widget.setDragDropMode(
            QAbstractItemView.DragDropMode.DropOnly
        )
        self.list_widget.viewport().setAcceptDrops(True)
        self.list_widget.setDefaultDropAction(Qt.DropAction.CopyAction)
        self.ui.gridLayout.addWidget(self.list_widget, 0, 0)
        self.list_widget.dragEnterEvent = self.dragEnterEvent
        self.list_widget.dropEvent = self.dropEvent

    def load_documents(self):
        self.list_widget.clear()
        documents = Document.objects.all()
        for doc in documents:
            self.add_document_item(doc)

    def add_document_item(self, document):
        widget = DocumentWidget(
            document, on_active_changed=self.on_active_changed
        )
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
