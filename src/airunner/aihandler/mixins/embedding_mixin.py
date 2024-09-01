import os
from airunner.enums import SignalCode


class EmbeddingMixin:
    def __init__(self):
        self.embeds_loaded = None

    @property
    def available_embeddings(self):
        return self.settings["embeddings"][self.settings["generator_settings"]["version"]]

    def load_learned_embed_in_clip(self):
        self.logger.debug("Loading embeddings")
        for embedding in self.available_embeddings:
            if embedding["active"]:
                path = os.path.expanduser(embedding["path"])
                if os.path.exists(path):
                    token = embedding["name"]
                    try:
                        self.pipe.load_textual_inversion(path, token=token, weight_name=path)
                    except Exception as e:
                        pass
            else:
                try:
                    self.pipe.unload_textual_inversion(embedding["name"])
                except ValueError:
                    pass
