import os

from airunner.settings import BASE_PATH


class LoraMixin:
    def __init__(self):
        self.loaded_lora: list = []
        self.disabled_lora: list = []
        self._available_lora: dict = None

    @property
    def available_lora(self):
        if self.settings["generator_settings"]["version"] in self.settings["lora"]:
            return self.settings["lora"][self.settings["generator_settings"]["version"]]
        return []

    def add_lora_to_pipe(self):
        self.loaded_lora = []
        self.apply_lora()

    def apply_lora(self):
        self.logger.debug("Adding LoRA to pipe")
        lora_path = os.path.expanduser(
            os.path.join(
                self.settings["path_settings"]["base_path"],
                "art/models",
                self.settings["generator_settings"]["version"],
                "lora"
            )
        )
        for lora in self.available_lora:
            if lora["enabled"] == False:
                continue
            for root, dirs, files in os.walk(lora_path):
                for file in files:
                    if file.startswith(lora["name"]):
                        filepath = os.path.join(root, file)
                        lora["path"] = filepath
                        break
            self.load_lora(lora)

    def on_update_lora_signal(self, lora: dict):
        if self.pipe is not None:
            if lora["enabled"]:
                self.load_lora(lora)
            else:
                self.remove_lora_from_pipe(lora)

    def load_lora(self, lora):
        if lora["path"] in self.disabled_lora:
            return
        try:
            filename = lora["path"].split("/")[-1]
            pathname = os.path.expanduser(
                os.path.join(
                    self.settings["path_settings"]["base_path"],
                    "art/models",
                    self.settings["generator_settings"]["version"],
                    "lora"
                )
            )
            for _lora in self.loaded_lora:
                if _lora["name"] == lora["name"] and _lora["path"] == lora["path"]:
                    return
            self.pipe.load_lora_weights(
                pathname,
                weight_name=filename
            )
            self.loaded_lora.append(lora)
        except AttributeError as e:
            self.logger.warning("This model does not support LORA")
            self.disable_lora(lora["path"])
        except RuntimeError:
            self.logger.warning("LORA could not be loaded")
            self.disable_lora(lora["path"])
        except ValueError:
            self.logger.warning("LORA could not be loaded")
            self.disable_lora(lora["path"])

    def remove_lora_from_pipe(self, lora:dict):
        for index, _lora in enumerate(self.loaded_lora):
            if _lora["name"] == lora["name"] and _lora["path"] == lora["path"]:
                self.loaded_lora.pop(index)
                break
        self.pipe.unload_lora_weights()
        self.apply_lora()

    def disable_lora(self, checkpoint_path):
        self.disabled_lora.append(checkpoint_path)
