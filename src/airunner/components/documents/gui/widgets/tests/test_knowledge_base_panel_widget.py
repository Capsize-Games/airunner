import os

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
