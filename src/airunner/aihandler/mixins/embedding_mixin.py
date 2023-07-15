import os
import torch
from aihandler.logger import logger
from aihandler.settings import MessageCode


class EmbeddingMixin:
    def load_learned_embed_in_clip(self):
        learned_embeds_path = self.settings_manager.settings.embeddings_path.get()
        if not os.path.exists(learned_embeds_path):
            learned_embeds_path = os.path.join(self.model_base_path, "embeddings")
        if self.embeds_loaded:
            return
        embeddings_not_supported = False
        self.embeds_loaded = True
        if os.path.exists(learned_embeds_path):
            logger.info("Loading embeddings...")
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
                        self.send_message({
                            "embedding_name": token,
                            "model_name": self.model,
                        }, MessageCode.EMBEDDING_LOAD_FAILED)
                        logger.warning(e)
            except AttributeError as e:
                if "load_textual_inversion" in str(e):
                    embeddings_not_supported = True
                else:
                    raise e
            except RuntimeError as e:
                embeddings_not_supported = True

            if embeddings_not_supported:
                logger.warning("Embeddings not supported in this model")
