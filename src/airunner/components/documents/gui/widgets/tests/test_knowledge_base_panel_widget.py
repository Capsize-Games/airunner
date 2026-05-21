import os
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from PySide6.QtWidgets import QApplication

from airunner.enums import SignalCode


def test_knowledge_base_panel_emits_index_signal():
    """The Index All button should emit RAG_INDEX_ALL_DOCUMENTS signal via the mediator."""
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    # Ensure we have a QApp instance for widget construction
    from airunner.components.documents.gui.widgets.knowledge_base_panel_widget import (
        KnowledgeBasePanelWidget,
    )

    app = QApplication.instance() or QApplication([])
    widget = KnowledgeBasePanelWidget()
    received = {"count": 0}

    def handler(data):
        received["count"] += 1

    widget.register(SignalCode.RAG_INDEX_ALL_DOCUMENTS, handler)
    widget._on_index_button_clicked()
    assert received["count"] == 1


def test_documents_widget_exposes_index_all_and_emits_signal():
    """DocumentsWidget should instantiate the KnowledgeBasePanel and allow emitting the index-all signal."""
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from airunner.components.documents.gui.widgets.documents import (
        DocumentsWidget,
    )
    from airunner.enums import SignalCode

    app = QApplication.instance() or QApplication([])
    doc_widget = DocumentsWidget()
    assert hasattr(doc_widget, "knowledgeBasePanelWidget")
    received = {"count": 0}

    def handler(data):
        received["count"] += 1

    doc_widget.register(SignalCode.RAG_INDEX_ALL_DOCUMENTS, handler)
    # Trigger the emit via the panel widget
    doc_widget.knowledgeBasePanelWidget._on_index_button_clicked()
    assert received["count"] == 1


def test_knowledge_base_panel_import_emits_collection_signal(monkeypatch):
    """Importing documents should notify the document collection UI."""
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from airunner.components.documents.gui.widgets.knowledge_base_panel_widget import (
        KnowledgeBasePanelWidget,
    )
    from airunner.components.documents.gui.widgets import (
        knowledge_base_panel_widget as module,
    )

    app = QApplication.instance() or QApplication([])
    widget = KnowledgeBasePanelWidget()
    received = {"count": 0}

    monkeypatch.setattr(
        module,
        "import_documents_to_library",
        lambda file_paths, destination_root: [
            "/tmp/imported-notes.md"
        ],
    )

    def handler(data):
        received["count"] += 1

    widget.register(SignalCode.DOCUMENT_COLLECTION_CHANGED, handler)
    widget._import_documents(["/tmp/source-notes.md"])

    assert received["count"] == 1


def test_documents_widget_expands_populated_sections():
    """Imported documents should be visible without manual tree expansion."""
    from airunner.components.documents.gui.widgets.documents import (
        DocumentsWidget,
    )

    expanded = []
    tree = SimpleNamespace(expand=lambda index: expanded.append(index))
    root_item = SimpleNamespace(rowCount=lambda: 2)
    populated_item = SimpleNamespace(rowCount=lambda: 1)
    empty_item = SimpleNamespace(rowCount=lambda: 0)
    model = SimpleNamespace(indexFromItem=lambda item: f"index:{id(item)}")
    widget = SimpleNamespace(
        ui=SimpleNamespace(documentsTreeView=tree),
        documents_model=model,
    )

    DocumentsWidget._expand_available_document_sections(
        widget,
        root_item,
        populated_item,
        empty_item,
    )

    assert expanded == [
        f"index:{id(root_item)}",
        f"index:{id(populated_item)}",
    ]


def test_available_documents_context_menu_offers_index(monkeypatch):
    """Unindexed available documents should expose an Index action."""
    from airunner.components.documents.gui.widgets import documents as module
    from airunner.components.documents.gui.widgets.documents import (
        DocumentsWidget,
    )

    action_labels = []

    class FakeSignal:
        def connect(self, callback):
            self.callback = callback

    class FakeAction:
        def __init__(self, text, parent):
            self.text = text
            self.triggered = FakeSignal()

    class FakeMenu:
        def __init__(self, parent):
            self.parent = parent

        def addAction(self, action):
            action_labels.append(action.text)

        def exec(self, _position):
            return None

    monkeypatch.setattr(module, "QAction", FakeAction)
    monkeypatch.setattr(module, "QMenu", FakeMenu)

    index = SimpleNamespace(isValid=lambda: True)
    item = SimpleNamespace(
        hasChildren=lambda: False,
        data=lambda role=None: "/tmp/doc.pdf",
    )
    view = SimpleNamespace(
        indexAt=lambda position: index,
        selectedIndexes=lambda: [index],
        viewport=lambda: SimpleNamespace(mapToGlobal=lambda position: position),
    )
    widget = SimpleNamespace(
        ui=SimpleNamespace(documentsTreeView=view),
        documents_model=SimpleNamespace(itemFromIndex=lambda _index: item),
    )

    DocumentsWidget.show_available_doc_context_menu(widget, object())

    assert "Index" in action_labels


def test_request_document_index_tracks_pending_activation(monkeypatch):
    """A queued index request should remember whether activation is needed."""
    from airunner.components.documents.gui.widgets import documents as module
    from airunner.components.documents.gui.widgets.documents import (
        DocumentsWidget,
    )

    doc = SimpleNamespace(id=7, indexed=False)
    create = Mock()
    monkeypatch.setattr(
        module,
        "Document",
        SimpleNamespace(
            objects=SimpleNamespace(
                filter_by=lambda path: [doc],
                create=create,
            )
        ),
    )

    widget = SimpleNamespace(
        _pending_document_index_requests={},
        _validate_document_file=lambda file_path: file_path,
        emit_signal=Mock(),
    )

    queued = DocumentsWidget._request_document_index(
        widget,
        "/tmp/doc.pdf",
    )
    queued_again = DocumentsWidget._request_document_index(
        widget,
        "/tmp/doc.pdf",
        activate_after_index=True,
    )

    assert queued is True
    assert queued_again is True
    assert widget._pending_document_index_requests["/tmp/doc.pdf"] is True
    widget.emit_signal.assert_called_once_with(
        SignalCode.RAG_INDEX_SELECTED_DOCUMENTS,
        {"file_paths": ["/tmp/doc.pdf"]},
    )
    create.assert_not_called()


def test_add_document_to_active_auto_indexes_unindexed_document(monkeypatch):
    """Add to Active should queue indexing instead of blocking the user."""
    from airunner.components.documents.gui.widgets import documents as module
    from airunner.components.documents.gui.widgets.documents import (
        DocumentsWidget,
    )

    monkeypatch.setattr(
        module,
        "Document",
        SimpleNamespace(
            objects=SimpleNamespace(
                filter_by=lambda path: [SimpleNamespace(indexed=False)],
            )
        ),
    )

    widget = SimpleNamespace(
        _validate_document_file=lambda file_path: file_path,
        _request_document_index=Mock(),
    )

    DocumentsWidget.add_document_to_active(widget, "/tmp/doc.pdf")

    widget._request_document_index.assert_called_once_with(
        "/tmp/doc.pdf",
        activate_after_index=True,
    )


def test_add_document_to_active_emits_collection_changed(monkeypatch):
    """Active-document adds should notify other widgets to sync."""
    from airunner.components.documents.gui.widgets import documents as module
    from airunner.components.documents.gui.widgets.documents import (
        DocumentsWidget,
    )

    update = Mock()
    monkeypatch.setattr(
        module,
        "Document",
        SimpleNamespace(
            objects=SimpleNamespace(
                filter_by=lambda path: [SimpleNamespace(id=5, indexed=True)],
                update=update,
                create=Mock(),
            )
        ),
    )

    active_model = SimpleNamespace(
        rowCount=lambda: 0,
        appendRow=Mock(),
    )
    widget = SimpleNamespace(
        _validate_document_file=lambda file_path: file_path,
        active_documents_model=active_model,
        _get_display_name=lambda path: "doc.pdf",
        logger=Mock(),
        emit_signal=Mock(),
    )

    DocumentsWidget.add_document_to_active(widget, "/tmp/doc.pdf")

    update.assert_called_once_with(pk=5, active=True)
    widget.emit_signal.assert_called_once_with(
        SignalCode.DOCUMENT_COLLECTION_CHANGED,
        {"paths": ["/tmp/doc.pdf"]},
    )


def test_remove_document_from_active_emits_collection_changed(monkeypatch):
    """Active-document removals should notify the chat prompt to detach."""
    from airunner.components.documents.gui.widgets import documents as module
    from airunner.components.documents.gui.widgets.documents import (
        DocumentsWidget,
    )

    update = Mock()
    monkeypatch.setattr(
        module,
        "Document",
        SimpleNamespace(
            objects=SimpleNamespace(
                filter_by=lambda path: [SimpleNamespace(id=7)],
                update=update,
            )
        ),
    )

    item = SimpleNamespace(data=lambda: "/tmp/doc.pdf")
    active_model = SimpleNamespace(
        rowCount=lambda: 1,
        item=lambda row, column: item,
        removeRow=Mock(),
    )
    widget = SimpleNamespace(
        active_documents_model=active_model,
        logger=Mock(),
        _get_display_name=lambda path: "doc.pdf",
        emit_signal=Mock(),
    )

    DocumentsWidget.remove_document_from_active(widget, "/tmp/doc.pdf")

    active_model.removeRow.assert_called_once_with(0)
    update.assert_called_once_with(pk=7, active=False)
    widget.emit_signal.assert_called_once_with(
        SignalCode.DOCUMENT_COLLECTION_CHANGED,
        {"paths": ["/tmp/doc.pdf"]},
    )


def test_on_document_indexed_refreshes_lists_for_index_only_requests(
    monkeypatch,
):
    """Index-only requests should not remain active after completion."""
    from airunner.components.documents.gui.widgets import documents as module
    from airunner.components.documents.gui.widgets.documents import (
        DocumentsWidget,
    )

    update = Mock()
    monkeypatch.setattr(
        module,
        "Document",
        SimpleNamespace(
            objects=SimpleNamespace(
                filter_by=lambda path: [SimpleNamespace(id=11)],
                update=update,
            )
        ),
    )

    widget = SimpleNamespace(
        _pending_document_index_requests={"/tmp/doc.pdf": False},
        _total_to_index=0,
        _current_indexing=0,
        refresh_documents_list=Mock(),
        refresh_active_documents_list=Mock(),
        logger=Mock(),
        _get_display_name=lambda path: "doc.pdf",
    )

    DocumentsWidget.on_document_indexed(widget, {"path": "/tmp/doc.pdf"})

    update.assert_called_once_with(pk=11, active=False)
    widget.refresh_documents_list.assert_called_once_with()
    widget.refresh_active_documents_list.assert_called_once_with()
    assert widget._pending_document_index_requests == {}


def test_document_library_changed_refreshes_views_and_emits_signal():
    """External file changes should refresh the knowledge-base views."""
    from airunner.components.documents.gui.widgets.documents import (
        DocumentsWidget,
    )

    widget = SimpleNamespace(
        refresh_documents_list=Mock(),
        refresh_active_documents_list=Mock(),
        emit_signal=Mock(),
    )

    DocumentsWidget._on_document_library_changed(widget, "/tmp/documents")

    widget.refresh_documents_list.assert_called_once_with()
    widget.refresh_active_documents_list.assert_called_once_with()
    widget.emit_signal.assert_called_once_with(
        SignalCode.DOCUMENT_COLLECTION_CHANGED,
        {"reason": "filesystem"},
    )


def test_on_document_index_failed_keeps_pending_request_for_deferred_retry():
    """Deferred indexing should stay pending until the retry succeeds."""
    from airunner.components.documents.gui.widgets.documents import (
        DocumentsWidget,
    )

    widget = SimpleNamespace(
        _pending_document_index_requests={"/tmp/doc.pdf": False},
        refresh_documents_list=Mock(),
        refresh_active_documents_list=Mock(),
        logger=Mock(),
        _get_display_name=lambda path: "doc.pdf",
    )

    DocumentsWidget.on_document_index_failed(
        widget,
        {
            "path": "/tmp/doc.pdf",
            "error": "Embedding model download in progress.",
            "deferred": True,
        },
    )

    assert widget._pending_document_index_requests == {
        "/tmp/doc.pdf": False,
    }
    widget.logger.info.assert_called_once()
    widget.logger.error.assert_not_called()
    widget.refresh_documents_list.assert_called_once_with()
    widget.refresh_active_documents_list.assert_called_once_with()
