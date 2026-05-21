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


def test_refresh_documents_list_updates_table_and_watch_paths():
    """Refreshing documents should update the table and watcher roots."""
    from airunner.components.documents.gui.widgets.documents import (
        DocumentsWidget,
    )

    widget = SimpleNamespace(
        refresh_active_documents_list=Mock(),
        _refresh_document_watch_paths=Mock(),
    )

    DocumentsWidget.refresh_documents_list(widget)

    widget.refresh_active_documents_list.assert_called_once_with()
    widget._refresh_document_watch_paths.assert_called_once_with()


def test_documents_table_context_menu_offers_index(monkeypatch):
    """Unindexed table rows should expose an Index action."""
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
    monkeypatch.setattr(
        module,
        "Document",
        SimpleNamespace(
            objects=SimpleNamespace(
                filter_by=lambda path: [
                    SimpleNamespace(active=False, indexed=False)
                ]
            )
        ),
    )

    index = SimpleNamespace(isValid=lambda: True, row=lambda: 0)
    table = SimpleNamespace(
        indexAt=lambda position: index,
        selectionModel=lambda: SimpleNamespace(
            selectedRows=lambda column: [index]
        ),
        item=lambda row, column: SimpleNamespace(
            data=lambda role=None: (
                "/tmp/doc.pdf"
                if role == Qt.ItemDataRole.UserRole and column == 0
                else None
            )
        ),
        viewport=lambda: SimpleNamespace(mapToGlobal=lambda position: position),
    )
    widget = SimpleNamespace(
        ui=SimpleNamespace(documentsTableWidget=table),
        _selected_document_table_paths=lambda: ["/tmp/doc.pdf"],
        _request_document_index=Mock(),
        add_document_to_active=Mock(),
        remove_document_from_active=Mock(),
        _get_display_name=lambda path: "doc.pdf",
        logger=Mock(),
        emit_signal=Mock(),
    )

    DocumentsWidget.show_documents_table_context_menu(widget, object())

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
        _document_index_failures={},
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

    widget = SimpleNamespace(
        _document_index_failures={},
        _validate_document_file=lambda file_path: file_path,
        _get_display_name=lambda path: "doc.pdf",
        refresh_active_documents_list=Mock(),
        logger=Mock(),
        emit_signal=Mock(),
    )

    DocumentsWidget.add_document_to_active(widget, "/tmp/doc.pdf")

    update.assert_called_once_with(pk=5, active=True)
    widget.refresh_active_documents_list.assert_called_once_with()
    widget.emit_signal.assert_called_once_with(
        SignalCode.DOCUMENT_COLLECTION_CHANGED,
        {"paths": ["/tmp/doc.pdf"]},
    )


def test_documents_widget_drop_imports_external_files(tmp_path):
    """External drops on the documents widget should import into the KB."""
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from airunner.components.documents.gui.widgets.documents import (
        DocumentsWidget,
    )

    app = QApplication.instance() or QApplication([])
    widget = DocumentsWidget()
    widget.path_settings.base_path = str(tmp_path / "airunner")
    widget.add_document_to_active = Mock()
    widget.knowledgeBasePanelWidget._import_documents = Mock(
        return_value=[
            str(tmp_path / "airunner/text/other/documents/book.pdf")
        ]
    )

    external_file = tmp_path / "outside-book.pdf"
    external_file.write_text("content", encoding="utf-8")

    handled = widget._handle_dropped_paths([str(external_file)])

    assert handled is True
    widget.knowledgeBasePanelWidget._import_documents.assert_called_once_with(
        [str(external_file)]
    )
    widget.add_document_to_active.assert_not_called()


def test_documents_widget_drop_activates_managed_files(tmp_path):
    """Managed-library drops should keep the activation behavior."""
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from airunner.components.documents.gui.widgets.documents import (
        DocumentsWidget,
    )

    app = QApplication.instance() or QApplication([])
    widget = DocumentsWidget()
    widget.path_settings.base_path = str(tmp_path / "airunner")
    os.makedirs(widget.documents_path, exist_ok=True)
    widget.add_document_to_active = Mock()
    widget.knowledgeBasePanelWidget._import_documents = Mock()

    managed_file = os.path.join(widget.documents_path, "managed-book.pdf")
    with open(managed_file, "w", encoding="utf-8") as handle:
        handle.write("content")

    handled = widget._handle_dropped_paths([managed_file])

    assert handled is True
    widget.add_document_to_active.assert_called_once_with(managed_file)
    widget.knowledgeBasePanelWidget._import_documents.assert_not_called()


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

    widget = SimpleNamespace(
        logger=Mock(),
        _get_display_name=lambda path: "doc.pdf",
        refresh_active_documents_list=Mock(),
        emit_signal=Mock(),
    )

    DocumentsWidget.remove_document_from_active(widget, "/tmp/doc.pdf")

    update.assert_called_once_with(pk=7, active=False)
    widget.refresh_active_documents_list.assert_called_once_with()
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
        _document_index_failures={"/tmp/doc.pdf": "boom"},
        _pending_document_index_requests={"/tmp/doc.pdf": False},
        _total_to_index=0,
        _current_indexing=0,
        refresh_documents_list=Mock(),
        logger=Mock(),
        _get_display_name=lambda path: "doc.pdf",
    )

    DocumentsWidget.on_document_indexed(widget, {"path": "/tmp/doc.pdf"})

    update.assert_called_once_with(pk=11, active=False)
    widget.refresh_documents_list.assert_called_once_with()
    assert widget._document_index_failures == {}
    assert widget._pending_document_index_requests == {}


def test_document_library_changed_refreshes_views_and_emits_signal():
    """External file changes should refresh the knowledge-base views."""
    from airunner.components.documents.gui.widgets.documents import (
        DocumentsWidget,
    )

    widget = SimpleNamespace(
        refresh_documents_list=Mock(),
        emit_signal=Mock(),
    )

    DocumentsWidget._on_document_library_changed(widget, "/tmp/documents")

    widget.refresh_documents_list.assert_called_once_with()
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
        _document_index_failures={},
        _pending_document_index_requests={"/tmp/doc.pdf": False},
        refresh_documents_list=Mock(),
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


def test_on_document_index_failed_records_error_for_documents_table():
    """Non-deferred indexing failures should surface in the error column."""
    from airunner.components.documents.gui.widgets.documents import (
        DocumentsWidget,
    )

    widget = SimpleNamespace(
        _document_index_failures={},
        _pending_document_index_requests={"/tmp/doc.pdf": True},
        refresh_documents_list=Mock(),
        refresh_active_documents_list=Mock(),
        logger=Mock(),
        _get_display_name=lambda path: "doc.pdf",
    )

    DocumentsWidget.on_document_index_failed(
        widget,
        {
            "path": "/tmp/doc.pdf",
            "error": "embedding failure",
            "deferred": False,
        },
    )

    assert widget._pending_document_index_requests == {}
    assert widget._document_index_failures == {
        "/tmp/doc.pdf": "embedding failure"
    }
    widget.logger.error.assert_called_once()
