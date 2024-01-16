import os
from airunner.aihandler.settings import LOG_LEVEL
from airunner.aihandler.logger import Logger

logger = Logger(prefix="LoraMixin")


class LoraMixin:
    @property
    def available_lora(self):
        return self.options.get(f"lora", [])

    def add_lora_to_pipe(self):
        self.loaded_lora = []
        self.apply_lora()

    def apply_lora(self):
        model_base_path = self.model_base_path
        lora_path = self.lora_path
        path = os.path.join(model_base_path, lora_path) if lora_path == "lora" else lora_path
        for lora in self.available_lora:
            if lora["enabled"] == False:
                continue
            filepath = None
            for root, dirs, files in os.walk(path):
                for file in files:
                    if file.startswith(lora["name"]):
                        filepath = os.path.join(root, file)
                        break
            self.load_lora(filepath, lora)

    def load_lora(self, checkpoint_path, lora):
        try:
            self.pipe.load_lora_weights(".", weight_name=checkpoint_path)
            self.loaded_lora.append({"name": lora["name"], "scale": lora["scale"]})
        except AttributeError:
            logger.warning("This model does not support LORA")
