import os

from PySide6.QtWidgets import QWidget, QSizePolicy, QApplication

from airunner.enums import SignalCode
from airunner.utils.models.scan_path_for_items import scan_path_for_items
from airunner.widgets.base_widget import BaseWidget
from airunner.widgets.embeddings.embedding_widget import EmbeddingWidget
from airunner.widgets.embeddings.templates.embeddings_container_ui import Ui_embeddings_container
from airunner.windows.main.embedding_mixin import EmbeddingMixin


class EmbeddingsContainerWidget(
    BaseWidget,
    EmbeddingMixin
):
    widget_class_ = Ui_embeddings_container
    _embedding_names = None
    embedding_widgets = {}
    bad_model_embedding_map = {}
    search_filter = ""
    spacer = None

    def __init__(self, *args, **kwargs):
        EmbeddingMixin.__init__(self)
        super().__init__(*args, **kwargs)
        self.initialized = False

    def showEvent(self, event):
        if not self.initialized:
            self.scan_for_embeddings()
            self.initialized = True

    def disable_embedding(self, name, model_name):
        if name not in self.embedding_widgets:
            return
        self.embedding_widgets[name].setEnabled(False)
        if name not in self.bad_model_embedding_map:
            self.bad_model_embedding_map[name] = []
        if model_name not in self.bad_model_embedding_map[name]:
            self.bad_model_embedding_map[name].append(model_name)

    def register_embedding_widget(self, name, widget):
        self.embedding_widgets[name] = widget

    def update_embedding_names(self):
        self._embedding_names = None
        self.load_embeddings()

    def load_embeddings(self):
        self._load_embeddings()

    def _load_embeddings(self):
        embeddings = self.get_embeddings({"name_filter": self.search_filter})

        self.clear_embedding_widgets()


        for embedding in embeddings:
            self.add_embedding(embedding)

        if not self.spacer:
            self.spacer = QWidget()
            self.spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.ui.scrollAreaWidgetContents.layout().addWidget(self.spacer)

    def add_embedding(self, embedding):
        embedding_widget = EmbeddingWidget(embedding=embedding)
        self.register_embedding_widget(embedding["name"], embedding_widget)
        self.ui.scrollAreaWidgetContents.layout().addWidget(embedding_widget)

    def action_clicked_button_scan_for_embeddings(self):
        self.scan_for_embeddings()

    def check_saved_embeddings(self):
        self.emit_signal(SignalCode.EMBEDDING_DELETE_MISSING_SIGNAL)

    def scan_for_embeddings(self):
        self.clear_embedding_widgets()
        settings = self.settings
        settings["embeddings"] = scan_path_for_items(
            base_path=self.settings["path_settings"]["base_path"],
            current_items=self.settings["embeddings"],
            scan_type="embeddings"
        )
        self.settings = settings
        self.save_settings()
        self.load_embeddings()

    def toggle_all_toggled(self, val):
        embedding_widgets = [
            self.ui.scrollAreaWidgetContents.layout().itemAt(i).widget()
            for i in range(self.ui.scrollAreaWidgetContents.layout().count())
            if isinstance(self.ui.scrollAreaWidgetContents.layout().itemAt(i).widget(), EmbeddingWidget)
        ]
        settings = self.settings
        for embedding_widget in embedding_widgets:
            embedding_widget.ui.enabledCheckbox.blockSignals(True)
            embedding_widget.action_toggled_embedding(val, False)
            embedding_widget.ui.enabledCheckbox.blockSignals(False)
        QApplication.processEvents()
        for index, _embedding in enumerate(self.settings["embeddings"][self.settings["generator_settings"]["version"]]):
            settings["embeddings"][self.settings["generator_settings"]["version"]][index]["active"] = val
        self.settings = settings

    def search_text_changed(self, val):
        self.search_filter = val
        try:
            self.clear_embedding_widgets()
        except RuntimeError as e:
            self.logger.error(f"Error clearing embedding widgets: {e}")

        try:
            self.load_embeddings()
        except RuntimeError as e:
            self.logger.error(f"Error loading embeddings: {e}")

    def clear_embedding_widgets(self):
        if self.spacer:
            try:
                self.ui.scrollAreaWidgetContents.layout().removeWidget(self.spacer)
            except RuntimeError as e:
                pass
        for i in reversed(range(self.ui.scrollAreaWidgetContents.layout().count())):
            widget = self.ui.scrollAreaWidgetContents.layout().itemAt(i).widget()
            if isinstance(widget, EmbeddingWidget):
                widget.deleteLater()
