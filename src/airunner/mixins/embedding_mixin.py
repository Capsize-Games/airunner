import os
import torch
from PyQt6.QtWidgets import QLabel, QWidget, QVBoxLayout


class EmbeddingMixin:
    _embedding_names = None
    settings_manager = None
    window = None

    @property
    def embedding_names(self):
        if self._embedding_names is None:
            self._embedding_names = self.get_list_of_available_embedding_names()
        return self._embedding_names

    def load_embeddings(self, tab):
        # create a widget that can be added to scroll area
        container = QWidget()
        container.setLayout(QVBoxLayout())
        print(self.embedding_names)
        for embedding_name in self.embedding_names:
            label = QLabel(embedding_name)
            # add label to the contianer
            container.layout().addWidget(label)
            # on double click of label insert it into the prompt
            label.mouseDoubleClickEvent = lambda event, _label=label: self.insert_into_prompt(_label.text())
        tab.embeddings.setWidget(container)

    def get_list_of_available_embedding_names(self):
        embeddings_folder = os.path.join(self.settings_manager.settings.model_base_path.get(), "embeddings")
        tokens = []
        print("embeddings_folder", embeddings_folder)
        if os.path.exists(embeddings_folder):
            for f in os.listdir(embeddings_folder):
                loaded_learned_embeds = torch.load(os.path.join(embeddings_folder, f), map_location="cpu")
                trained_token = list(loaded_learned_embeds.keys())[0]
                if trained_token == "string_to_token":
                    trained_token = loaded_learned_embeds["name"]
                tokens.append(trained_token)
        return tokens

    def insert_into_prompt(self, text):
        # insert text into current tab prompt
        tab = self.window.tabWidget.currentWidget()
        tab.prompt.insertPlainText(text)