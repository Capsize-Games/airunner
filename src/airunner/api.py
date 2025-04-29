from typing import Optional, Dict

from PySide6.QtWidgets import QDialog, QVBoxLayout
from PySide6.QtCore import QObject

from airunner.app import App
from airunner.handlers.llm.llm_request import LLMRequest
from airunner.handlers.llm.llm_response import LLMResponse
from airunner.handlers.stablediffusion.image_request import ImageRequest
from airunner.enums import SignalCode, LLMActionType
from airunner.setup_database import setup_database
from airunner.utils.application.create_worker import create_worker
from airunner.gui.utils.ui_dispatcher import render_ui_from_spec
from airunner.utils.application.ui_loader import (
    load_ui_file,
    load_ui_from_string,
)


class API(App):
    def __init__(self, *args, **kwargs):
        # Extract the initialize_app flag and pass the rest to the parent App class
        self._initialize_app = kwargs.pop("initialize_app", True)
        initialize_gui = kwargs.pop("initialize_gui", True)
        self.signal_handlers = {
            SignalCode.SHOW_WINDOW_SIGNAL: self.show_hello_world_window,
            SignalCode.SHOW_DYNAMIC_UI_FROM_STRING_SIGNAL: self.show_dynamic_ui_from_string,
        }
        super().__init__(*args, initialize_gui=initialize_gui, **kwargs)
        self.initialize_model_scanner()

    def initialize_model_scanner(self):
        from airunner.workers.model_scanner_worker import (
            ModelScannerWorker,
        )

        if self._initialize_app:
            setup_database()
            self.model_scanner_worker = create_worker(ModelScannerWorker)
            self.model_scanner_worker.add_to_queue("scan_for_models")

    def send_llm_request(
        self,
        prompt: str,
        llm_request: Optional[LLMRequest] = None,
        action: LLMActionType = LLMActionType.CHAT,
        do_tts_reply: bool = True,
    ):
        """
        Send a request to the LLM with the given prompt and action.

        :param prompt: The prompt to send to the LLM.
        :param llm_request: Optional LLMRequest object.
        :param action: The action type for the request.
        :param do_tts_reply: Whether to do text-to-speech reply.
        :return: None
        """
        llm_request = llm_request or LLMRequest.from_default()
        llm_request.do_tts_reply = do_tts_reply

        self.emit_signal(
            SignalCode.LLM_TEXT_GENERATE_REQUEST_SIGNAL,
            {
                "llm_request": True,
                "request_data": {
                    "action": action,
                    "prompt": prompt,
                    "llm_request": llm_request,
                    "do_tts_reply": do_tts_reply,
                },
            },
        )

    def send_tts_request(self, response: LLMResponse):
        """
        Send a TTS request with the given response."

        :param response: The LLMResponse object.
        :return: None
        """
        self.emit_signal(
            SignalCode.LLM_TEXT_STREAMED_SIGNAL, {"response": response}
        )

    def send_image_request(self, image_request: Optional[ImageRequest] = None):
        """ "
        Send a request to the image generator with the given request.
        :param image_request: Optional ImageRequest object.
        :return: None
        """
        image_request = image_request or ImageRequest()
        self.emit_signal(
            SignalCode.DO_GENERATE_SIGNAL, {"image_request": image_request}
        )

    def show_hello_world_window(self):
        """
        Display a 'Hello, world!' popup window using the UI dispatcher.
        """
        spec = {
            "type": "window",
            "title": "Hello Window",
            "layout": "vertical",
            "widgets": [{"type": "label", "text": "Hello, world!"}],
        }
        dialog = QDialog(self.app.main_window)
        dialog.setWindowTitle(spec.get("title", "Untitled"))
        render_ui_from_spec(spec, dialog)
        dialog.exec()

    def show_dynamic_ui(self, ui_file_path: str):
        """
        Load and display a .ui file dynamically as a popup window.

        :param ui_file_path: Path to the .ui file.
        """
        dialog = QDialog(self.app.main_window)
        dialog.setWindowTitle("Dynamic UI")
        widget = load_ui_file(ui_file_path, dialog)
        layout = dialog.layout() or QVBoxLayout(dialog)
        layout.addWidget(widget)
        dialog.setLayout(layout)
        dialog.exec()

    def show_dynamic_ui_from_string(self, data: Dict):
        """
        Load and display a .ui file dynamically from a string as a popup window.

        :param ui_content: The content of the .ui file as a string.
        """
        ui_content = data.get("ui_content", "")

        class SignalHandler(QObject):
            def __init__(self, api: API):
                self.api = api
                super().__init__()

            def click_me_button(self):
                self.api.emit_signal(SignalCode.SHOW_WINDOW_SIGNAL)

        signal_handler = SignalHandler(api=self)
        dialog = QDialog(self.app.main_window)
        dialog.setWindowTitle("Dynamic UI with Signal")
        widget = load_ui_from_string(ui_content, dialog, signal_handler)
        layout = dialog.layout() or QVBoxLayout(dialog)
        layout.addWidget(widget)
        dialog.setLayout(layout)
        dialog.exec()
