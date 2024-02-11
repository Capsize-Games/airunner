from airunner.enums import SignalCode


class LoraMixin:
    def __init__(self):
        self.register(SignalCode.LORA_UPDATE_SIGNAL, self.on_update_lora_signal)
        self.register(SignalCode.LORA_ADD_SIGNAL, self.on_add_lora_signal)

    def on_add_lora_signal(self, params):
        settings = self.settings
        name = params["name"]
        path = params["path"]
        # ensure we have a unique name and path combo
        for index, lora in enumerate(settings["lora"]):
            if not lora:
                del settings["lora"][index]
                continue
            if lora["name"] == name and lora["path"] == path:
                return
        lora = {
            'name': params.get("name", ""),
            'path': params.get("path", ""),
            'scale': params.get("scale", 1),
            'enabled': params.get("enabled", True),
            'loaded': params.get("loaded", False),
            'trigger_word': params.get("trigger_word", ""),
            'version': params.get("version", "SD 1.5"),
        }
        settings["lora"].append(lora)
        self.settings = settings
        return lora
    
    def on_update_lora_signal(self, lora):
        settings = self.settings
        for index, _lora in enumerate(self.settings["lora"]):
            if _lora["name"] == lora["name"] and _lora["path"] == lora["path"]:
                settings["lora"][index] = lora
                self.settings = settings
                return
