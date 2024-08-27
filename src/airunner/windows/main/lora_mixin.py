from airunner.enums import SignalCode


class LoraMixin:
    def __init__(self):
        settings = self.settings
        settings["lora"] = scan_path_for_lora(settings["lora"])
        self.settings = settings

    def on_update_lora_signal(self, lora: dict):
        settings = self.settings
        for version, current_lora in self.settings["lora"].items():
            for index, _lora in enumerate(current_lora):
                if _lora["name"] == lora["name"] and _lora["path"] == lora["path"]:
                    settings["lora"][version][index] = lora
                    self.settings = settings
                    return
