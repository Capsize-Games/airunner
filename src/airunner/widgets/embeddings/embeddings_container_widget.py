import os

from airunner.data.models import Embedding
from airunner.utils import get_session, save_session
from airunner.widgets.base_widget import BaseWidget
from airunner.widgets.embeddings.embedding_widget import EmbeddingWidget
from airunner.widgets.embeddings.templates.embeddings_container_ui import Ui_embeddings_container


class EmbeddingsContainerWidget(BaseWidget):
    widget_class_ = Ui_embeddings_container

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.load_embeddings()
        self.scan_for_embeddings()

    def load_embeddings(self):
        session = get_session()
        embeddings = session.query(Embedding).all()
        for embedding in embeddings:
            self.add_embedding(embedding)

    def add_embedding(self, embedding):
        embedding_widget = EmbeddingWidget(name=embedding.name)
        self.ui.scrollAreaWidgetContents.layout().addWidget(embedding_widget)

    def action_clicked_button_scan_for_embeddings(self):
        self.scan_for_embeddings()

    def scan_for_embeddings(self):
        # recursively scan for embedding model files in the embeddings path
        # for each embedding model file, create an Embedding model
        # add the Embedding model to the database
        # add the Embedding model to the UI
        session = get_session()
        embeddings_path = self.settings_manager.path_settings.embeddings_path
        with os.scandir(embeddings_path) as dir_object:
            for entry in dir_object:
                if entry.is_file():  # ckpt or safetensors file
                    # check if entry.name is in ckpt, safetensors or pt files:
                    if entry.name.endswith(".ckpt") or entry.name.endswith(".safetensors") or entry.name.endswith(".pt"):
                        name = entry.name.replace(".ckpt", "").replace(".safetensors", "").replace(".pt", "")
                        embedding = Embedding(name=name, path=entry.path)
                        session.add(embedding)
        save_session(session)
