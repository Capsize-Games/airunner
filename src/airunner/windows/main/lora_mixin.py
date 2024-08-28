from airunner.enums import SignalCode
from airunner.utils.models.scan_path_for_items import scan_path_for_items


class LoraMixin:
    def __init__(self):
        settings = self.settings
        settings["lora"] = scan_path_for_items(self.settings["path_settings"]["base_path"], settings["lora"])
        self.settings = settings
        self.save_settings()
