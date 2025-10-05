from airunner.components.application.api.api_service_base import APIServiceBase
from airunner.enums import SignalCode


class DocumentEditorService(APIServiceBase):
    def run_script(self, document_path: str):
        self.emit_signal(
            SignalCode.RUN_SCRIPT, {"document_path": document_path}
        )

    def new_document(self):
        self.emit_signal(SignalCode.NEW_DOCUMENT, {})