import os


class EmbeddingMixin:
    def __init__(self):
        self.embeds_loaded = None

    @property
    def available_embeddings(self):
        return self.settings["embeddings"][self.settings["generator_settings"]["version"]]

    def load_learned_embed_in_clip(self):
        self.logger.debug("Loading embeddings")
        for embedding in self.available_embeddings:
            path = os.path.expanduser(embedding["path"])
            if embedding["active"]:
                if os.path.exists(path):
                    token = embedding["name"]
                    try:
                        self.pipe.load_textual_inversion(path, token=token, weight_name=path)
                    except Exception as e:
                        if "already in tokenizer" not in str(e):
                            self.logger.error(f"Failed to load embedding {token}: {e}")
            else:
                try:
                    self.pipe.unload_textual_inversion(embedding["name"])
                except ValueError as e:
                    self.logger.error(f"Failed to unload embedding {embedding['name']}: {e}")
