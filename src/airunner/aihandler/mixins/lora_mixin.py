import os


class LoraMixin:
    def __init__(self):
        self.loaded_lora = None
        self.disabled_lora = {}
        self._available_lora = None

    @property
    def available_lora(self):
        if not self._available_lora:
            self._available_lora = {}
            available_lora = self.options.get(f"lora", [])
            for lora in available_lora:
                self._available_lora[lora["version"]] = lora
        return self._available_lora

    def add_lora_to_pipe(self):
        self.loaded_lora = []
        self.apply_lora()

    def apply_lora(self):
        model_base_path = self.model_base_path
        lora_path = self.lora_path
        path = os.path.join(model_base_path, lora_path) if lora_path == "lora" else lora_path
        if self.model_version not in self.available_lora:
            return
        for lora in self.available_lora[self.model_version]:
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
        if self.model_base_path in self.disabled_lora:
            if checkpoint_path in self.disabled_lora[self.model_base_path]:
                return

        try:
            self.pipe.load_lora_weights(".", weight_name=checkpoint_path)
            self.loaded_lora.append({"name": lora["name"], "scale": lora["scale"]})
        except AttributeError:
            self.logger.warning("This model does not support LORA")
            self.disable_lora(checkpoint_path)
        except RuntimeError:
            self.logger.warning("LORA could not be loaded")
            self.disable_lora(checkpoint_path)

    def disable_lora(self, checkpoint_path):
        if self.model_base_path not in self.disabled_lora:
            self.disabled_lora[self.model_base_path] = []
        self.disabled_lora[self.model_base_path].append(checkpoint_path)
