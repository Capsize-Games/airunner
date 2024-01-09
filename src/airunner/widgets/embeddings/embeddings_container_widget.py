import os

from PyQt6.QtCore import pyqtSlot
from PyQt6.QtWidgets import QWidget, QSizePolicy

from airunner.aihandler.enums import MessageCode
from airunner.data.models import Embedding
from airunner.utils import get_session
from airunner.widgets.base_widget import BaseWidget
from airunner.widgets.embeddings.embedding_widget import EmbeddingWidget
from airunner.widgets.embeddings.templates.embeddings_container_ui import Ui_embeddings_container


class EmbeddingsContainerWidget(BaseWidget):
    widget_class_ = Ui_embeddings_container
    _embedding_names = None
    embedding_widgets = {}
    bad_model_embedding_map = {}
    search_filter = ""
    spacer = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.app.generator_tab_changed_signal.connect(self.handle_generator_tab_changed)
        self.app.tab_section_changed_signal.connect(self.handle_tab_section_changed)
        self.settings_manager.changed_signal.connect(self.handle_changed_signal)
        self.app.message_var.my_signal.connect(self.message_handler)

        self.scan_for_embeddings()

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

    def enable_embeddings(self):
        for name in self.embedding_widgets.keys():
            enable = True
            if name in self.bad_model_embedding_map:
                if self.app.model in self.bad_model_embedding_map[name]:
                    enable = False
            self.embedding_widgets[name].setEnabled(enable)

    def handle_embedding_load_failed(self, message):
        # TODO:
        #  on model change, re-enable the buttons
        embedding_name = message["embedding_name"]
        model_name = message["model_name"]
        self.disable_embedding(embedding_name, model_name)

    def update_embedding_names(self):
        self._embedding_names = None
        for tab_name in self.app.tabs.keys():
            tab = self.app.tabs[tab_name]
            # clear embeddings
            try:
                tab.embeddings.widget().deleteLater()
            except AttributeError:
                pass
            self.load_embeddings(tab)

    def handle_generator_tab_changed(self):
        self.enable_embeddings()

    def handle_tab_section_changed(self):
        self.enable_embeddings()

    def handle_changed_signal(self, key):
        if key == "embeddings_path":
            self.update_embedding_names()
        elif key == "generator.model":
            self.enable_embeddings()

    @pyqtSlot(dict)
    def message_handler(self, response: dict):
        code = response["code"]
        message = response["message"]
        if code == MessageCode.EMBEDDING_LOAD_FAILED:
            self.handle_embedding_load_failed(message)

    def load_embeddings(self):
        self.clear_embedding_widgets()
        
        session = get_session()
        embeddings = session.query(Embedding).filter(
            Embedding.name.like(f"%{self.search_filter}%") if self.search_filter != "" else True).all()
        for embedding in embeddings:
            self.add_embedding(embedding)
        
        if not self.spacer:
            self.spacer = QWidget()
            self.spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.ui.scrollAreaWidgetContents.layout().addWidget(self.spacer)

    def add_embedding(self, embedding):
        embedding_widget = EmbeddingWidget(embedding=embedding)
        self.register_embedding_widget(embedding.name, embedding_widget)
        self.ui.scrollAreaWidgetContents.layout().addWidget(embedding_widget)

    def action_clicked_button_scan_for_embeddings(self):
        self.scan_for_embeddings()
    
    def check_saved_embeddings(self):
        session = get_session()
        embeddings = session.query(Embedding).all()
        for embedding in embeddings:
            if not os.path.exists(embedding.path):
                session.delete(embedding)

    def scan_for_embeddings(self):
        # recursively scan for embedding model files in the embeddings path
        # for each embedding model file, create an Embedding model
        # add the Embedding model to the database
        # add the Embedding model to the UI
        self.check_saved_embeddings()

        session = get_session()
        embeddings_path = self.settings_manager.path_settings.embeddings_path

        if os.path.exists(embeddings_path):
            for root, dirs, _ in os.walk(embeddings_path):
                for dir in dirs:
                    path = os.path.join(root, dir)
                    for entry in os.scandir(path):
                        if entry.is_file() and entry.name.endswith((".ckpt", ".safetensors", ".pt")):
                            name = os.path.splitext(entry.name)[0]
                            embedding = session.query(Embedding).filter_by(name=name).first()
                            if not embedding:
                                embedding = Embedding(name=name, path=entry.path)
                                session.add(embedding)
            session.commit()
        self.load_embeddings()

    def toggle_all_toggled(self, checked):
        for i in range(self.ui.embeddings.widget().layout().count()):
            widget = self.ui.embeddings.widget().layout().itemAt(i).widget()
            if widget:
                try:
                    widget.ui.enabledCheckbox.setChecked(checked)
                except AttributeError:
                    continue

    def search_text_changed(self, val):
        self.search_filter = val
        self.clear_embedding_widgets()
        self.load_embeddings()
    
    def clear_embedding_widgets(self):
        if self.spacer:
            self.ui.scrollAreaWidgetContents.layout().removeWidget(self.spacer)
        for i in reversed(range(self.ui.scrollAreaWidgetContents.layout().count())):
            widget = self.ui.scrollAreaWidgetContents.layout().itemAt(i).widget()
            if isinstance(widget, EmbeddingWidget):
                widget.deleteLater()