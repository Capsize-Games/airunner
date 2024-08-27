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
                BASE_PATH,
                "art/models",
                self.settings["generator_settings"]["version"],
                "lora"
            )
        )
        for lora in self.available_lora:
            if lora["enabled"] == False:
                continue
            filepath = None
            for root, dirs, files in os.walk(lora_path):
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
        except ValueError:
            self.logger.warning("LORA could not be loaded")
            self.disable_lora(checkpoint_path)

    def disable_lora(self, checkpoint_path):
        self.disabled_lora.append(checkpoint_path)
