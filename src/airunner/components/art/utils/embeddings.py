from typing import List, Optional, Type

from airunner_model.models.embedding import Embedding


def get_embeddings_by_version(version) -> Optional[List[Type[Embedding]]]:
    embeddings = Embedding.objects.all()
    return [
        embedding for embedding in embeddings if embedding.version == version
    ]
