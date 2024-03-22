import os

from airunner.enums import SignalCode


class EmbeddingMixin:
    def __init__(self):
        self.embeds_loaded = None
        self._available_embeddings = {}

    @property
    def available_embeddings(self):
        if not self._available_embeddings:
            self._available_embeddings = {}
            available_embeddings = self.settings["embeddings"]
            for embedding in available_embeddings:
                self._available_embeddings[embedding["version"]] = embedding
        return self._available_embeddings

    def load_learned_embed_in_clip(self):
        learned_embeds_path = self.settings["path_settings"]["embeddings_model_path"]
        if not os.path.exists(learned_embeds_path):
            self.logger.warning("Embeddings path does not exist")
            return

        if self.embeds_loaded:
            return
        embeddings_not_supported = False
        self.embeds_loaded = True
        if os.path.exists(learned_embeds_path):
            self.logger.debug("Loading embeddings")
            try:
                for f in os.listdir(learned_embeds_path):
                    path = os.path.join(learned_embeds_path, f)
                    words = f.split(".")
                    if words[-1] in ["pt", "ckpt", "pth", "safetensors"]:
                        words = words[:-1]
                    token = ".".join(words).lower()
                    try:
                        self.pipe.load_textual_inversion(path, token=token, weight_name=f)
                    except Exception as e:
                        if "already in tokenizer vocabulary" not in str(e):
                            self.emit_signal(SignalCode.EMBEDDING_LOAD_FAILED_SIGNAL, {
                                'embedding_name': token,
                                'model_name': self.model,
                            })
                            self.logger.warning(e)
            except AttributeError as e:
                if "load_textual_inversion" in str(e):
                    embeddings_not_supported = True
                else:
                    raise e
            except RuntimeError as e:
                embeddings_not_supported = True

            if embeddings_not_supported:
                self.logger.warning("Embeddings not supported in this model")
