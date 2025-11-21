from typing import Dict

from PySide6.QtCore import Slot
from PySide6.QtGui import QIcon

from airunner.enums import SignalCode
from airunner.components.application.gui.widgets.base_widget import BaseWidget
from airunner.components.home_stage.gui.widgets.templates.knowledge_base_panel_ui import (
    Ui_knowledge_base_panel,
)


class KnowledgeBasePanelWidget(BaseWidget):
    """Small widget for showing document statistics and manual indexing controls.

    This class wraps the generated `Ui_knowledge_base_panel` UI so it can be
    reused in `DocumentsWidget` and other places. It emits the existing
    application signals for RAG indexing actions and listens for progress
    updates.
    """

    widget_class_ = Ui_knowledge_base_panel

    def __init__(self, *args, **kwargs):
        # Track indexing progress locally
        self._total = 0
        self._current = 0
        self._document_name = ""
        self.signal_handlers = {
            SignalCode.RAG_INDEXING_PROGRESS: self.on_indexing_progress,
            SignalCode.RAG_INDEXING_COMPLETE: self.on_indexing_complete,
        }
        super().__init__(*args, **kwargs)

        # Wire up buttons
        try:
            self.ui.index_button.clicked.connect(self._on_index_button_clicked)
        except Exception:
            pass
        try:
            self.ui.cancel_button.clicked.connect(
                self._on_cancel_button_clicked
            )
        except Exception:
            pass

    @Slot()
    def _on_index_button_clicked(self):
        """Emit a RAG index-all signal.

        The existing worker/agent mixins expect SignalCode.RAG_INDEX_ALL_DOCUMENTS
        in order to begin the indexed flow. Provide a simple payload for
        compatibility.
        """
        self.logger.info(
            "KnowledgeBasePanel::Index All clicked - emitting RAG_INDEX_ALL_DOCUMENTS"
        )
        # show infinite progress bar
        self.ui.progress_bar.setRange(0, 0)
        self.emit_signal(SignalCode.RAG_INDEX_ALL_DOCUMENTS, {})

    @Slot()
    def _on_cancel_button_clicked(self):
        """Emit a cancel signal for in-progress indexing flows."""
        self.logger.info(
            "KnowledgeBasePanel::Cancel clicked - emitting RAG_INDEX_CANCEL"
        )
        self.emit_signal(SignalCode.RAG_INDEX_CANCEL, {})

    def on_indexing_progress(self, data: Dict):
        try:
            progress = int(data.get("progress", 0))
            current = int(data.get("current", 0))
            total = int(data.get("total", 0))
            document_name = data.get("documentName", "")
            self._current = current
            self._total = total
            self._document_name = document_name
            if self.ui.progress_bar.maximum() == 0:
                self.ui.progress_bar.setRange(0, 100)
            self.ui.progress_bar.setValue(progress)
        except Exception:
            pass

    def on_indexing_complete(self, data: Dict):
        try:
            self.ui.progress_bar.setValue(100)
            self.ui.progress_text.setText("Complete")
        except Exception:
            pass
