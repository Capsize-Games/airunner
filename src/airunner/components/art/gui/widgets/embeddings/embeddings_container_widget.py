import os
from typing import Any, Dict
from PySide6.QtCore import Slot, QSize, QTimer, Qt
from PySide6.QtWidgets import QWidget, QSizePolicy, QApplication

from airunner.enums import SignalCode, ModelType, ModelStatus
from airunner.components.art.utils.embeddings import (
    get_embeddings_by_version,
)
from airunner.components.application.gui.widgets.base_widget import BaseWidget
from airunner.components.art.gui.widgets.embeddings.embedding_widget import (
    EmbeddingWidget,
)
from airunner.components.art.gui.widgets.embeddings.templates.embeddings_container_ui import (
    Ui_embeddings_container,
)


class EmbeddingsContainerWidget(BaseWidget):
    widget_class_ = Ui_embeddings_container
    search_filter = ""
    spacer = None

    def __init__(self, *args, **kwargs):
        self.signal_handlers = {
            SignalCode.APPLICATION_SETTINGS_CHANGED_SIGNAL: (
                self.on_application_settings_changed_signal
            ),
            SignalCode.EMBEDDING_UPDATED_SIGNAL: (
                self.on_embedding_updated_signal
            ),
            SignalCode.MODEL_STATUS_CHANGED_SIGNAL: (
                self.on_model_status_changed_signal
            ),
            SignalCode.EMBEDDING_STATUS_CHANGED: (
                self.on_embedding_modified
            ),
            SignalCode.EMBEDDING_DELETE_SIGNAL: self._delete_embedding,
        }
        self._version = None
        super().__init__(*args, **kwargs)
        self.initialized = False
        self._deleting = False
        self.ui.loading_icon.hide()
        self.ui.loading_icon.set_size(
            spinner_size=QSize(30, 30), label_size=QSize(24, 24)
        )
        self._apply_button_enabled = False
        self.ui.apply_embeddings_button.setEnabled(
            self._apply_button_enabled
        )

    @Slot()
    def action_clicked_button_scan_for_embeddings(self):
        self.scan_for_embeddings()
        self.load_embeddings()

    @Slot()
    def apply_embeddings(self):
        self._apply_button_enabled = False
        self.api.art.embeddings.update()

    @Slot(str)
    def search_text_changed(self, val):
        self.search_filter = val
        self.load_embeddings(force_reload=True)

    def on_model_status_changed_signal(self, data):
        model = data["model"]
        status = data["status"]
        if model is ModelType.SD:
            if status is ModelStatus.LOADING:
                self._disable_form()
            else:
                self._enable_form()

    def on_embedding_modified(self):
        self._apply_button_enabled = True
        self.ui.apply_embeddings_button.setEnabled(
            self._apply_button_enabled
        )

    @Slot(bool)
    def toggle_all_toggled(self, val):
        embedding_widgets = [
            self.ui.embeddings_scroll_area.widget()
            .layout()
            .itemAt(i)
            .widget()
            for i in range(
                self.ui.embeddings_scroll_area.widget()
                .layout()
                .count()
            )
            if isinstance(
                self.ui.embeddings_scroll_area.widget()
                .layout()
                .itemAt(i)
                .widget(),
                EmbeddingWidget,
            )
        ]
        for embedding in embedding_widgets:
            embedding.ui.enabledCheckbox.blockSignals(True)
            embedding.action_toggled_embedding(val)
            embedding.ui.enabledCheckbox.blockSignals(False)

    def on_application_settings_changed_signal(self):
        self.load_embeddings()

    def on_embedding_updated_signal(self):
        self._enable_form()

    def _delete_embedding(self, data: Dict):
        self._deleting = True
        embedding_widget = data["embedding_widget"]

        # Remove from database via daemon
        embedding_widget.embedding.delete()

        self._apply_button_enabled = True
        self.ui.apply_embeddings_button.setEnabled(
            self._apply_button_enabled
        )
        self.load_embeddings(force_reload=True)
        self._deleting = False

    def showEvent(self, event):
        if not self.initialized:
            self.scan_for_embeddings()
            self.initialized = True
        self.load_embeddings(force_reload=True)

    def load_embeddings(self, force_reload: bool = False):
        version = self.generator_settings.version

        if self._version is None or self._version != version or force_reload:
            self._version = version
            self.clear_embedding_widgets()
            embeddings = get_embeddings_by_version(version)
            if embeddings:
                filtered_embeddings = [
                    embedding
                    for embedding in embeddings
                    if self.search_filter.lower()
                    in embedding.name.lower()
                ]
                for embedding in filtered_embeddings:
                    self._add_embedding(embedding)
                self.add_spacer()

    def remove_spacer(self):
        if self.spacer:
            self.ui.scrollAreaWidgetContents.layout().removeWidget(
                self.spacer
            )
            self.spacer.setParent(None)
            self.spacer.deleteLater()
            self.spacer = None

    def add_spacer(self):
        self.remove_spacer()

        self.spacer = QWidget()
        self.spacer.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self.spacer.setMinimumHeight(100)

        self.ui.scrollAreaWidgetContents.layout().addWidget(self.spacer)
        self.ui.scrollAreaWidgetContents.layout().update()
        QApplication.processEvents()
        QTimer.singleShot(
            50,
            lambda: self.ui.scrollAreaWidgetContents.layout().update(),
        )

    def _add_embedding(self, embedding):
        if embedding is None:
            return
        embedding_widget = EmbeddingWidget(embedding=embedding)
        self.ui.scrollAreaWidgetContents.layout().addWidget(
            embedding_widget
        )

    def scan_for_embeddings(self):
        self.load_embeddings(force_reload=True)

    def clear_embedding_widgets(self):
        if self.spacer:
            try:
                self.ui.scrollAreaWidgetContents.layout().removeWidget(
                    self.spacer
                )
            except RuntimeError:
                pass
        for i in reversed(
            range(self.ui.scrollAreaWidgetContents.layout().count())
        ):
            widget = (
                self.ui.scrollAreaWidgetContents.layout()
                .itemAt(i)
                .widget()
            )
            if isinstance(widget, EmbeddingWidget):
                widget.deleteLater()

    def _disable_form(self):
        self.ui.apply_embeddings_button.setEnabled(
            self._apply_button_enabled
        )
        self.ui.toggle_all_embeddings.setEnabled(False)
        self.ui.loading_icon.show()
        self._toggle_embedding_widgets(False)

    def _enable_form(self):
        self.ui.apply_embeddings_button.setEnabled(
            self._apply_button_enabled
        )
        self.ui.toggle_all_embeddings.setEnabled(True)
        self.ui.loading_icon.hide()
        self._toggle_embedding_widgets(True)

    def _toggle_embedding_widgets(self, enable: bool):
        for i in range(
            self.ui.embeddings_scroll_area.widget()
            .layout()
            .count()
        ):
            embedding_widget = (
                self.ui.embeddings_scroll_area.widget()
                .layout()
                .itemAt(i)
                .widget()
            )
            if isinstance(embedding_widget, EmbeddingWidget):
                if enable:
                    embedding_widget.enable_embedding_widget()
                else:
                    embedding_widget.disable_embedding_widget()
