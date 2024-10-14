import os
from airunner.enums import SignalCode
from airunner.utils.models.scan_path_for_items import scan_path_for_embeddings


class EmbeddingMixin:
    @property
    def __embeddings(self):
        return self.get_embeddings_by_version(self.generator_settings.version)

    def get_embeddings(self, message: dict = None):
        name_filter = message.get("name_filter") if message is not None else ""
        embeddings = []

        for embedding in self.__embeddings:
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

    def delete_missing_embeddings(self):
        embeddings = self.get_embeddings()
        for embedding in embeddings:
            if not os.path.exists(embedding["path"]):
                self._delete_embedding(embedding)
    
    def _delete_embedding(self, embedding):
        for index, _embedding in enumerate(self.embeddings):
            if _embedding.name == embedding.name and _embedding.path == embedding.path:
                self._delete_embedding(embedding)
                return

    def scan_for_embeddings(self):
        embeddings = scan_path_for_embeddings(self.path_settings.base_path)
        self.update_embeddings(embeddings)
        self.emit_signal(
            SignalCode.EMBEDDING_GET_ALL_RESULTS_SIGNAL,
            {
                "embeddings": self.get_embeddings_by_version(self.generator_settings.version)
            }
        )
