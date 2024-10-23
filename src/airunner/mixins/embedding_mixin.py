import os
from functools import partial

import torch
from PyQt6 import uic
from PyQt6.QtWidgets import QLabel, QWidget, QVBoxLayout


class EmbeddingMixin:
    _embedding_names = None

    @property
    def embedding_names(self):
        if self._embedding_names is None:
            self._embedding_names = self.get_list_of_available_embedding_names()
        return self._embedding_names

    def initialize(self):
        # listen to self.settings_manager.settings.embeddings_path and update self.embedding_names on change
        self.settings_manager.settings.embeddings_path.my_signal.connect(self.update_embedding_names)

        for tab_name in self.tabs.keys():
            tab = self.tabs[tab_name]
            self.load_embeddings(tab)

    def update_embedding_names(self, _):
        self._embedding_names = None
        for tab_name in self.tabs.keys():
            tab = self.tabs[tab_name]
            # clear embeddings
            try:
                tab.embeddings.widget().deleteLater()
            except AttributeError:
                pass
            self.load_embeddings(tab)

    def load_embeddings(self, tab):
        container = QWidget()
        container.setLayout(QVBoxLayout())
        for embedding_name in self.embedding_names:
            widget = uic.loadUi("pyqt/embedding.ui")
            widget.label.setText(embedding_name)
            widget.to_prompt_button.clicked.connect(partial(self.insert_into_prompt, f"{embedding_name}"))
            widget.to_negative_prompt_button.clicked.connect(partial(self.insert_into_prompt, f"{embedding_name}", True))
            container.layout().addWidget(widget)
        container.layout().addStretch()
        tab.embeddings.setWidget(container)

    def get_list_of_available_embedding_names(self):
        embeddings_path = self.settings_manager.settings.embeddings_path.get() or "embeddings"
        if embeddings_path == "embeddings":
            embeddings_path = os.path.join(self.settings_manager.settings.model_base_path.get(), embeddings_path)
        return self.find_embeddings_in_path(embeddings_path)

    def find_embeddings_in_path(self, embeddings_path, tokens=None):
        if tokens is None:
            tokens = []
        if not os.path.exists(embeddings_path):
            return tokens
        if os.path.exists(embeddings_path):
            for f in os.listdir(embeddings_path):
                # check if f is directory
                if os.path.isdir(os.path.join(embeddings_path, f)):
                    return self.find_embeddings_in_path(os.path.join(embeddings_path, f), tokens)
                words = f.split(".")
                # if the last word is pt, ckpt, or pth, then join all words except the last one
                if words[-1] in ["pt", "ckpt", "pth", "safetensors"]:
                    words = words[:-1]
                words = ".".join(words).lower()
                tokens.append(words)
        return tokens

    def insert_into_prompt(self, text, negative_prompt=False):
        tab = self.tabWidget.currentWidget()
        if negative_prompt:
            current_text = tab.negative_prompt.toPlainText()
            text = f"{current_text}, {text}" if current_text != "" else text
            tab.negative_prompt.setPlainText(text)
        else:
            current_text = tab.prompt.toPlainText()
            text = f"{current_text}, {text}" if current_text != "" else text
            tab.prompt.setPlainText(text)
