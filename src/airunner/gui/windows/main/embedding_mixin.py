from typing import List, Type
import os
from airunner.enums import SignalCode
from airunner.utils.art.embeddings import get_embeddings_by_version
from airunner.utils.models import scan_path_for_embeddings
from airunner.data.models import Embedding


class EmbeddingMixin:
    @property
    def embeddings(self) -> List[Type[Embedding]]:
        return Embedding.objects.all()

    @property
    def __embeddings(self):
        return get_embeddings_by_version(self.generator_settings.version)

    def get_embeddings(self, message: dict = None):
        name_filter = message.get("name_filter") if message is not None else ""
        embeddings = []

        for embedding in self.__embeddings:
            if name_filter == "":
                embeddings.append(embedding)
                continue
            if name_filter in embedding["name"]:
                embeddings.append(embedding)
        self.api.art.embeddings.get_all_results(embeddings=embeddings)
        return embeddings

    def delete_missing_embeddings(self):
        embeddings = self.get_embeddings()
        for embedding in embeddings:
            if not os.path.exists(embedding["path"]):
                self._delete_embedding(embedding)

    def _delete_embedding(self, embedding):
        for index, _embedding in enumerate(self.embeddings):
            if (
                _embedding.name == embedding.name
                and _embedding.path == embedding.path
            ):
                self._delete_embedding(embedding)
                return

    def scan_for_embeddings(self):
        embeddings = scan_path_for_embeddings(self.path_settings.base_path)
        self.update_embeddings(embeddings)
        self.api.art.get_all_results(
            embeddings=get_embeddings_by_version(
                self.generator_settings.version
            )
        )
