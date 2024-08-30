import os

from airunner.enums import ModelType, ModelStatus
from airunner.settings import BASE_PATH


class LoraMixin:
    def __init__(self):
        self.loaded_lora: list = []
        self.disabled_lora: list = []
        self._available_lora: dict = None
        settings = self.settings
        self.lora_path = os.path.expanduser(
            os.path.join(
                settings["path_settings"]["base_path"],
                "art/models",
                settings["generator_settings"]["version"],
                "lora"
            )
        )

    @property
    def available_lora(self):
        if self.settings["generator_settings"]["version"] in self.settings["lora"]:
            return self.settings["lora"][self.settings["generator_settings"]["version"]]
        return []

    def add_lora_to_pipe(self):
        """
        Called when stable diffusion handler is loaded
        """
        try:
            self.loaded_lora = []
            self.apply_all_lora()
        except Exception as e:
            self.logger.error(f"Error adding lora to pipe: {e}")

    def on_update_lora_signal(self, message: dict):
        """
        Called when LORA status is updated and signal is emitted
        """
        if self.pipe is not None:
            self.apply_all_lora(message["lora"])

    def apply_all_lora(self, loras: list=None):
        """
        Apply / remove all LORA to the pipe. If none are passed, all available LORA will be considered.
        """
        loras = loras or self.available_lora
        if len(loras) == 0:
            return
        self.remove_lora_from_pipe()
        if self.pipe is not None:
            self.change_model_status(ModelType.SD, ModelStatus.LOADING)
            for lora in loras:
                if lora["enabled"]:
                    self.load_lora(lora)
            self.change_model_status(ModelType.SD, ModelStatus.LOADED)
            if len(self.loaded_lora):
                self.logger.debug("LoRA loaded")

    def has_lora_changed(self):
        """
        Check if there are any changes in the available LORA compared to the loaded LORA.
        Return True if there are changes, otherwise False.
        """
        available_lora = self.available_lora
        loaded_lora_paths = {lora["path"] for lora in self.loaded_lora}

        for lora in available_lora:
            if lora["enabled"] and lora["path"] not in loaded_lora_paths:
                return True

        return False

    def load_lora(self, lora):
        if lora["path"] in self.disabled_lora:
            return

        if not self.has_lora_changed():
            return

        try:
            filename = lora["path"].split("/")[-1]
            for _lora in self.loaded_lora:
                if _lora["name"] == lora["name"] and _lora["path"] == lora["path"]:
                    return
            self.pipe.load_lora_weights(
                self.lora_path,
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

    def remove_lora_from_pipe(self):
        self.loaded_lora = []
        self.pipe.unload_lora_weights()

    def disable_lora(self, checkpoint_path):
        self.disabled_lora.append(checkpoint_path)
