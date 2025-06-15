from airunner.components.application.api.api_service_base import APIServiceBase
from airunner.enums import SignalCode


class BrowserAPIService(APIServiceBase):
    def navigate_to_url(self, url: str):
        print("BROWSER API SERVICE NAVIGATE TO URL", url)
        self.emit_signal(SignalCode.BROWSER_NAVIGATE_SIGNAL, {"url": url})
