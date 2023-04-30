import os
import torch
from PyQt6.QtWidgets import QLabel, QWidget, QVBoxLayout


class EmbeddingMixin:
    _embedding_names = None

    @property
    def embedding_names(self):
        if self._embedding_names is None:
            self._embedding_names = self.get_list_of_available_embedding_names()
        return self._embedding_names

    def load_embeddings(self, tab):
        container = QWidget()
        container.setLayout(QVBoxLayout())
        for embedding_name in self.embedding_names:
            label = QLabel(embedding_name)
            container.layout().addWidget(label)
            label.mouseDoubleClickEvent = lambda event, _label=label: self.insert_into_prompt(_label.text())
        container.layout().addStretch()
        tab.embeddings.setWidget(container)

    def get_list_of_available_embedding_names(self):
        embeddings_folder = os.path.join(self.settings_manager.settings.model_base_path.get(), "embeddings")
        tokens = []
        if os.path.exists(embeddings_folder):
            for f in os.listdir(embeddings_folder):
                loaded_learned_embeds = torch.load(os.path.join(embeddings_folder, f), map_location="cpu")
                trained_token = list(loaded_learned_embeds.keys())[0]
                if trained_token == "string_to_token":
                    trained_token = loaded_learned_embeds["name"]
                tokens.append(trained_token)
        return tokens

    def insert_into_prompt(self, text):
        tab = self.window.tabWidget.currentWidget()
        tab.prompt.insertPlainText(text)
