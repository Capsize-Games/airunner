from airunner.components.application.api.api_service_base import APIServiceBase
from airunner.enums import SignalCode


class LoraAPIServices(APIServiceBase):
    def update(self):
        self.emit_signal(SignalCode.LORA_UPDATE_SIGNAL)

    def status_changed(self):
        self.emit_signal(SignalCode.LORA_STATUS_CHANGED)

    def delete(self, lora_widget):
        self.emit_signal(
            SignalCode.LORA_DELETE_SIGNAL,
            {"lora_widget": lora_widget},
        )
