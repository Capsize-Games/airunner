from typing import Any, List, Optional

from airunner.daemon_client.resource_store import get_resource_store


def get_embeddings_by_version(version) -> Optional[List[Any]]:
    embeddings = get_resource_store().query("Embedding")
    return [
        embedding for embedding in embeddings if embedding.version == version
    ]
