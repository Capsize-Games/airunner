import os


class LoraMixin:
    def __init__(self):
        self.loaded_lora: list = []
        self.disabled_lora: list = []
        self._available_lora: dict = None

    @property
    def available_lora(self):
        if not self._available_lora:
            _available_lora = {}
            for index, lora in enumerate(self.settings["lora"]):
                if lora["version"] not in _available_lora:
                    _available_lora[lora["version"]] = []
                _available_lora[lora["version"]].append(lora)
            self._available_lora = _available_lora
        return self._available_lora

    def add_lora_to_pipe(self):
        self.loaded_lora = []
        self.apply_lora()

    def apply_lora(self):
        self.logger.debug("Adding LoRA to pipe")
        model_base_path = self.settings["path_settings"]["base_path"]
        lora_path = self.settings["path_settings"]["lora_model_path"]
        model_version = self.model["version"]
        path = os.path.join(model_base_path, lora_path) if lora_path == "lora" else lora_path
        if model_version not in self.available_lora:
            return
        for lora in self.available_lora[model_version]:
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
        if checkpoint_path in self.disabled_lora:
            return
        try:
            self.pipe.load_lora_weights(".", weight_name=checkpoint_path)
            self.loaded_lora.append({"name": lora["name"], "scale": lora["scale"]})
        except AttributeError as e:
            self.logger.warning("This model does not support LORA")
            self.disable_lora(checkpoint_path)
        except RuntimeError:
            self.logger.warning("LORA could not be loaded")
            self.disable_lora(checkpoint_path)

    def disable_lora(self, checkpoint_path):
        self.disabled_lora.append(checkpoint_path)
