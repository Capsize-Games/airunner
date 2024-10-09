import os

from PySide6.QtCore import Slot, QThread, QSize
from PySide6.QtWidgets import QWidget, QSizePolicy

from airunner.enums import SignalCode, ModelType, ModelStatus
from airunner.utils.models.scan_path_for_items import scan_path_for_embeddings
from airunner.widgets.base_widget import BaseWidget
from airunner.widgets.embeddings.embedding_widget import EmbeddingWidget
from airunner.widgets.embeddings.templates.embeddings_container_ui import Ui_embeddings_container
from airunner.workers.directory_watcher import DirectoryWatcher


class EmbeddingsContainerWidget(BaseWidget):
    widget_class_ = Ui_embeddings_container
    search_filter = ""
    spacer = None

    def __init__(self, *args, **kwargs):
        self._version = None
        super().__init__(*args, **kwargs)
        self.initialized = False
        self._deleting = False
        self.register(SignalCode.APPLICATION_SETTINGS_CHANGED_SIGNAL, self.on_application_settings_changed_signal)
        self.register(SignalCode.EMBEDDING_UPDATED_SIGNAL, self.on_embedding_updated_signal)
        self.register(SignalCode.MODEL_STATUS_CHANGED_SIGNAL, self.on_model_status_changed_signal)
        self.register(SignalCode.EMBEDDING_STATUS_CHANGED, self.on_embedding_modified)
        self.register(SignalCode.EMBEDDING_DELETE_SIGNAL, self.delete_embedding)
        self.ui.loading_icon.hide()
        self.ui.loading_icon.set_size(spinner_size=QSize(30, 30), label_size=QSize(24, 24))
        self._apply_button_enabled = False
        self.ui.apply_embeddings_button.setEnabled(self._apply_button_enabled)
        self._scanner_worker = DirectoryWatcher(self.path_settings.base_path, self._scan_path_for_embeddings)
        self._scanner_worker.scan_completed.connect(self.on_scan_completed)
        self._scanner_thread = QThread()
        self._scanner_worker.moveToThread(self._scanner_thread)
        self._scanner_thread.started.connect(self._scanner_worker.run)
        self._scanner_thread.start()

    def _scan_path_for_embeddings(self, path) -> bool:
        if self._deleting:
            return False
        return scan_path_for_embeddings(path)

    @Slot(bool)
    def on_scan_completed(self, force_reload: bool):
        self.load_embeddings(force_reload=force_reload)

    @Slot()
    def action_clicked_button_scan_for_embeddings(self):
        self.scan_for_embeddings()
        self.load_embeddings()

    @Slot()
    def apply_embeddings(self):
        self._apply_button_enabled = False
        self.emit_signal(SignalCode.EMBEDDING_UPDATE_SIGNAL)

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
        self.ui.apply_embeddings_button.setEnabled(self._apply_button_enabled)

    @Slot(bool)
    def toggle_all_toggled(self, val):
        embedding_widgets = [
            self.ui.embeddings_scroll_area.widget().layout().itemAt(i).widget()
            for i in range(self.ui.embeddings_scroll_area.widget().layout().count())
            if isinstance(self.ui.embeddings_scroll_area.widget().layout().itemAt(i).widget(), EmbeddingWidget)
        ]
        for embedding in embedding_widgets:
            embedding.ui.enabledCheckbox.blockSignals(True)
            embedding.action_toggled_embedding(val)
            embedding.ui.enabledCheckbox.blockSignals(False)

    def on_application_settings_changed_signal(self):
        self.load_embeddings()

    def on_embedding_updated_signal(self):
        self._enable_form()

    def delete_embedding(self, data):
        self._deleting = True
        embedding_widget = data["embedding_widget"]

        # Delete the lora from disc
        lora_path = os.path.expanduser(
            os.path.join(
                self.path_settings.base_path,
                "art/models",
                self._version,
                "embeddings"
            )
        )
        lora_file = embedding_widget.embedding.name
        for dirpath, dirnames, filenames in os.walk(lora_path):
            for file in filenames:
                if file.startswith(lora_file):
                    os.remove(os.path.join(dirpath, file))
                    break

        # Remove lora from database
        session = self.db_handler.get_db_session()
        session.delete(embedding_widget.embedding)
        session.commit()
        session.close()

        self._apply_button_enabled = True
        self.ui.apply_embeddings_button.setEnabled(self._apply_button_enabled)
        self.load_embeddings(force_reload=True)
        self._deleting = False

    def showEvent(self, event):
        if not self.initialized:
            self.scan_for_embeddings()
            self.initialized = True
        self.load_embeddings()

    def load_embeddings(self, force_reload:bool=False):
        version = self.generator_settings.version

        if self._version is None or self._version != version or force_reload:
            self._version = version
            self.clear_embedding_widgets()
            embeddings = self.get_embeddings_by_version(version)
            if embeddings:
                self.remove_spacer()
                filtered_embeddings = [
                    embedding for embedding in embeddings
                    if self.search_filter.lower() in embedding.name.lower()
                ]
                for embedding in filtered_embeddings:
                    self.add_embedding(embedding)
                self.add_spacer()

    def remove_spacer(self):
        # remove spacer from end of self.ui.scrollAreaWidgetContents.layout()
        if self.spacer:
            self.ui.scrollAreaWidgetContents.layout().removeWidget(self.spacer)

    def add_spacer(self):
        # add spacer to end of self.ui.scrollAreaWidgetContents.layout()
        if not self.spacer:
            self.spacer = QWidget()
            self.spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        else:
            self.remove_spacer()
        self.ui.scrollAreaWidgetContents.layout().addWidget(self.spacer)

    def add_embedding(self, embedding):
        if embedding is None:
            return
        embedding_widget = EmbeddingWidget(embedding=embedding)
        self.ui.scrollAreaWidgetContents.layout().addWidget(embedding_widget)

    def scan_for_embeddings(self):
        force_reload = scan_path_for_embeddings(self.path_settings.base_path)
        self.load_embeddings(force_reload=force_reload)

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

    def _disable_form(self):
        self.ui.apply_embeddings_button.setEnabled(self._apply_button_enabled)
        self.ui.toggle_all_embeddings.setEnabled(False)
        self.ui.loading_icon.show()
        self._toggle_embedding_widgets(False)

    def _enable_form(self):
        self.ui.apply_embeddings_button.setEnabled(self._apply_button_enabled)
        self.ui.toggle_all_embeddings.setEnabled(True)
        self.ui.loading_icon.hide()
        self._toggle_embedding_widgets(True)

    def _toggle_embedding_widgets(self, enable: bool):
        for i in range(self.ui.embeddings_scroll_area.widget().layout().count()):
            embedding_widget = self.ui.embeddings_scroll_area.widget().layout().itemAt(i).widget()
            if isinstance(embedding_widget, EmbeddingWidget):
                if enable:
                    embedding_widget.enable_embedding_widget()
                else:
                    embedding_widget.disable_embedding_widget()
