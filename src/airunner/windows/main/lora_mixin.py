from airunner.enums import SignalCode
from airunner.utils.models.scan_path_for_lora import scan_path_for_lora


class LoraMixin:
    def __init__(self):
        settings = self.settings
        settings["lora"] = scan_path_for_lora(settings["lora"])
        self.settings = settings
        self.save_settings()
