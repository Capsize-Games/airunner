import os
from airunner.enums import SignalCode
from airunner.utils.models.scan_path_for_items import scan_path_for_items


class EmbeddingMixin:
    def update_embedding(self, embedding: dict):
        settings = self.settings
        for index, _embedding in enumerate(self.settings["embeddings"]):
            if _embedding["name"] == embedding["name"] and _embedding["path"] == embedding["path"]:
                settings["embeddings"][index] = embedding
                self.settings = settings
                return

    def get_embeddings(self, message: dict = None):
        name_filter = message.get("name_filter") if message is not None else ""
        embeddings = []

        for embedding in self.settings["embeddings"]:
            if name_filter == "":
                embeddings.append(embedding)
                continue
            if name_filter in embedding["name"]:
                embeddings.append(embedding)
        self.emit_signal(
            SignalCode.EMBEDDING_GET_ALL_RESULTS_SIGNAL,
            {
                "embeddings": embeddings
            }
        )
        return embeddings

    def delete_missing_embeddings(self, _message: dict):
        embeddings = self.get_embeddings()
        for embedding in embeddings:
            if not os.path.exists(embedding["path"]):
                self.delete_embedding(embedding)
    
    def delete_embedding(self, embedding):
        settings = self.settings
        for index, _embedding in enumerate(self.settings["embeddings"]):
            if _embedding["name"] == embedding["name"] and _embedding["path"] == embedding["path"]:
                del settings["embeddings"][index]
                self.settings = settings
                return

    def scan_for_embeddings(self, _message: dict):
        print("SCAN FOR EMBEDDINGS CALLED FROM EMBEDDING MIXIN")
        settings = self.settings
        self.settings["embeddings"] = scan_path_for_items(self.settings["path_settings"]["base_path"], settings["embeddings"], scan_type="embeddings")
        self.settings = settings
        self.save_settings()
