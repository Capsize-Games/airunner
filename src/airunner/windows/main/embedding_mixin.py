import os

from airunner.service_locator import ServiceLocator


class EmbeddingMixin:
    def __init__(self):
        ServiceLocator.register("get_embeddings", self.get_embeddings)
        ServiceLocator.register("delete_missing_embeddings", self.delete_missing_embeddings)
        ServiceLocator.register("scan_for_embeddings", self.scan_for_embeddings)

    def add_embedding(self, params):
        settings = self.settings
        name = params["name"]
        path = params["path"]
        # ensure we have a unique name and path combo
        for index, embedding in enumerate(settings["embeddings"]):
            if not embedding:
                del settings["embeddings"][index]
                continue
            if embedding["name"] == name and embedding["path"] == path:
                return
        embedding = dict(
            name=params.get("name", ""),
            path=params.get("path", ""),
            tags=params.get("tags", ""),
            active=params.get("active", True),
            version=params.get("version", "SD 1.5"),
        )
        settings["embeddings"].append(embedding)
        self.settings = settings
        return embedding
    
    def update_embedding(self, embedding):
        settings = self.settings
        for index, _embedding in enumerate(self.settings["embeddings"]):
            if _embedding["name"] == embedding["name"] and _embedding["path"] == embedding["path"]:
                settings["embeddings"][index] = embedding
                self.settings = settings
                return

    def get_embeddings(self, name_filter=""):
        embeddings = []
        for embedding in self.settings["embeddings"]:
            if name_filter == "":
                embeddings.append(embedding)
                continue
            if name_filter in embedding["name"]:
                embeddings.append(embedding)
        return embeddings

    def delete_missing_embeddings(self):
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
    
    def scan_for_embeddings(self):
        embeddings_path = self.path_settings["embeddings_model_path"]
        if os.path.exists(embeddings_path):
            for root, dirs, _ in os.walk(embeddings_path):
                for dir in dirs:
                    version = dir.split("/")[-1]
                    path = os.path.join(root, dir)
                    for entry in os.scandir(path):
                        if entry.is_file() and entry.name.endswith((".ckpt", ".safetensors", ".pt")):
                            name = os.path.splitext(entry.name)[0]
                            embedding = dict(name=name, path=entry.path, version=version)
                            self.add_embedding(embedding)
        self.delete_missing_embeddings()